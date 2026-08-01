from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from packaging.specifiers import SpecifierSet
from pdm.models.backends import PDMBackend
from pdm.models.candidates import Candidate
from pdm.models.repositories.lock import LockedRepository, Package
from pdm.models.requirements import NamedRequirement, Requirement, parse_requirement
from pdm.utils import cd

from pdm_dockerize.commands import (
    _adapt_locked_dependencies,
    _adapt_locked_members,
    _adapt_requirements_for_lockfile,
    _adapted_locked_repository,
)


def _make_req(name: str, extras: tuple[str, ...] | None = None) -> Requirement:
    """Create a NamedRequirement with optional extras."""
    return NamedRequirement(name=name, extras=extras)


def _make_repo(packages: dict[str, list[str] | None]) -> MagicMock:
    """Create a mock locked repository from an identity key to dependency lines mapping.

    Keys are identity strings such as ``"pkg"`` or ``"pkg[extra]"`` — they are
    expanded into ``CandidateKey`` tuples internally.
    """
    locked_repo = MagicMock()
    locked_repo.packages = {
        (key, None, None, False): MagicMock(dependencies=dependencies)
        for key, dependencies in packages.items()
    }
    return locked_repo


def _make_project(package_keys: set[str]) -> MagicMock:
    """Create a mock project whose locked repository has the given identity keys."""
    project = MagicMock()
    project.get_locked_repository.return_value = _make_repo(dict.fromkeys(package_keys, []))
    return project


class TestAdaptRequirementsForLockfile:
    """Tests for _adapt_requirements_for_lockfile()."""

    def test_no_extras_unchanged(self):
        """Requirements without extras pass through unchanged."""
        reqs = [_make_req("foo"), _make_req("bar")]
        project = _make_project({"foo", "bar"})

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 2
        assert result[0].identify() == "foo"
        assert result[1].identify() == "bar"

    def test_single_extra_unchanged(self):
        """Requirements with a single extra pass through unchanged."""
        reqs = [_make_req("foo", extras=("extra1",))]
        project = _make_project({"foo", "foo[extra1]"})

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 1
        assert result[0].identify() == "foo[extra1]"

    def test_combined_extras_with_combined_lockfile_unchanged(self):
        """Combined extras pass through when lockfile has a combined entry (resolvelib-style)."""
        reqs = [_make_req("foo", extras=("extra1", "extra2"))]
        project = _make_project({"foo", "foo[extra1,extra2]"})

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 1
        assert result[0].identify() == "foo[extra1,extra2]"

    def test_combined_extras_split_for_uv_lockfile(self):
        """Combined extras are split when lockfile has separate entries (uv-style)."""
        reqs = [_make_req("foo", extras=("extra1", "extra2"))]
        project = _make_project({"foo", "foo[extra1]", "foo[extra2]"})

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 2
        identities = {r.identify() for r in result}
        assert identities == {"foo[extra1]", "foo[extra2]"}

    def test_combined_extras_split_preserves_other_fields(self):
        """Splitting preserves all other requirement fields (specifier, marker, etc.)."""

        req = _make_req("foo", extras=("extra1", "extra2"))
        req.specifier = SpecifierSet(">=1.0")
        project = _make_project({"foo", "foo[extra1]", "foo[extra2]"})

        result = _adapt_requirements_for_lockfile([req], project)

        assert len(result) == 2
        for r in result:
            assert r.specifier == SpecifierSet(">=1.0")
            assert r.name == "foo"

    def test_mixed_requirements(self):
        """Mix of plain, single-extra, and multi-extra requirements."""
        reqs = [
            _make_req("plain"),
            _make_req("single", extras=("x",)),
            _make_req("multi", extras=("a", "b")),
        ]
        project = _make_project(
            {
                "plain",
                "single",
                "single[x]",
                "multi",
                "multi[a]",
                "multi[b]",
            }
        )

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 4
        identities = [r.identify() for r in result]
        assert identities[0] == "plain"
        assert identities[1] == "single[x]"
        assert set(identities[2:]) == {"multi[a]", "multi[b]"}

    def test_partial_split_entries_no_split(self):
        """If only some split entries exist, don't split (safety fallback)."""
        reqs = [_make_req("foo", extras=("extra1", "extra2"))]
        # Only one of the two split entries exists — should NOT split
        project = _make_project({"foo", "foo[extra1]"})

        result = _adapt_requirements_for_lockfile(reqs, project)

        # Requirement passes through unchanged since not all split entries are present
        assert len(result) == 1
        assert result[0].identify() == "foo[extra1,extra2]"

    def test_three_extras_split(self):
        """Splitting works for three or more extras."""
        reqs = [_make_req("foo", extras=("a", "b", "c"))]
        project = _make_project({"foo", "foo[a]", "foo[b]", "foo[c]"})

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 3
        identities = {r.identify() for r in result}
        assert identities == {"foo[a]", "foo[b]", "foo[c]"}

    def test_multiple_packages_with_split_extras(self):
        """Multiple packages each with split extras."""
        reqs = [
            _make_req("foo", extras=("a", "b")),
            _make_req("bar", extras=("x", "y")),
        ]
        project = _make_project(
            {
                "foo",
                "foo[a]",
                "foo[b]",
                "bar",
                "bar[x]",
                "bar[y]",
            }
        )

        result = _adapt_requirements_for_lockfile(reqs, project)

        assert len(result) == 4
        identities = {r.identify() for r in result}
        assert identities == {"foo[a]", "foo[b]", "bar[x]", "bar[y]"}

    def test_empty_requirements_list(self):
        """Empty requirements list returns empty list."""
        project = _make_project(set())

        result = _adapt_requirements_for_lockfile([], project)

        assert result == []


def _dependencies(repo: MagicMock, key: str) -> list[str] | None:
    """Get back the (possibly adapted) dependency lines of a locked package."""
    return repo.packages[(key, None, None, False)].dependencies


class TestAdaptLockedDependencies:
    """Tests for _adapt_locked_dependencies()."""

    def test_transitive_combined_extras_split_for_uv_lockfile(self):
        """A locked dependency with combined extras is split into single-extra ones."""
        repo = _make_repo(
            {
                "root": ["foo[extra1,extra2]"],
                "foo": None,
                "foo[extra1]": None,
                "foo[extra2]": None,
            }
        )

        _adapt_locked_dependencies(repo)

        assert _dependencies(repo, "root") == ["foo[extra1]", "foo[extra2]"]

    def test_transitive_combined_extras_kept_for_resolvelib_lockfile(self):
        """A locked dependency is left untouched when the combined entry exists."""
        repo = _make_repo({"root": ["foo[extra1,extra2]"], "foo[extra1,extra2]": None})

        _adapt_locked_dependencies(repo)

        assert _dependencies(repo, "root") == ["foo[extra1,extra2]"]

    def test_partial_split_entries_no_split(self):
        """If only some split entries exist, don't split (safety fallback)."""
        repo = _make_repo({"root": ["foo[extra1,extra2]"], "foo[extra1]": None})

        _adapt_locked_dependencies(repo)

        assert _dependencies(repo, "root") == ["foo[extra1,extra2]"]

    def test_other_dependencies_untouched(self):
        """Plain and single-extra dependencies are preserved as-is."""
        repo = _make_repo(
            {
                "root": ["plain>=1.0", "single[x]", "foo[a,b]"],
                "plain": None,
                "single[x]": None,
                "foo[a]": None,
                "foo[b]": None,
            }
        )

        _adapt_locked_dependencies(repo)

        assert _dependencies(repo, "root") == ["plain>=1.0", "single[x]", "foo[a]", "foo[b]"]

    def test_specifier_and_marker_preserved(self):
        """Splitting preserves the version specifier and the environment marker."""
        repo = _make_repo(
            {
                "root": ['foo[a,b]>=1.0; python_version >= "3.13"'],
                "foo[a]": None,
                "foo[b]": None,
            }
        )

        _adapt_locked_dependencies(repo)

        lines = _dependencies(repo, "root")
        assert lines is not None
        assert len(lines) == 2
        for line, extra in zip(lines, ("a", "b"), strict=True):
            assert line.startswith(f"foo[{extra}]>=1.0")
            assert 'python_version >= "3.13"' in line

    @pytest.mark.parametrize("dependencies", [None, []], ids=["none", "empty"])
    def test_packages_without_dependencies(self, dependencies: list[str] | None):
        """Packages without dependencies are skipped."""
        repo = _make_repo({"root": dependencies})

        _adapt_locked_dependencies(repo)

        assert _dependencies(repo, "root") == dependencies


class TestAdaptedLockedRepository:
    """Tests for _adapted_locked_repository()."""

    class FakeProject:
        """A minimal stand-in for a real ``Project``.

        ``MagicMock`` can not be used here: the context manager restores the
        original method by deleting the instance attribute shadowing it, which
        mocks handle differently from regular objects.
        """

        def __init__(self, repo: MagicMock | None = None) -> None:
            self.repo = repo

        def iter_workspace_dependencies(self) -> list[Requirement]:
            return []

        def get_locked_repository(self, *args, **kwargs) -> MagicMock | None:
            return self.repo

    def test_adapts_every_repository_and_restores_the_method(self):
        """Repositories built in the context are adapted, and the method is restored after."""
        repo = _make_repo({"root": ["foo[a,b]"], "foo[a]": None, "foo[b]": None})
        project = self.FakeProject(repo)

        with _adapted_locked_repository(project):
            assert _dependencies(project.get_locked_repository(), "root") == ["foo[a]", "foo[b]"]

        assert "get_locked_repository" not in vars(project)
        assert project.get_locked_repository() is repo

    def test_method_restored_on_error(self):
        """The original method is restored even when the context body raises."""
        project = self.FakeProject()

        with pytest.raises(RuntimeError), _adapted_locked_repository(project):
            raise RuntimeError("boom")

        assert "get_locked_repository" not in vars(project)


class TestAdaptLockedMembers:
    """Tests for _adapt_locked_members()."""

    @staticmethod
    def _member_req(tmp_path: Path, name: str = "member-a") -> Requirement:
        """The path requirement a workspace root implicitly depends on."""
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
        with cd(tmp_path):
            req = parse_requirement(f"./{name}", True)
            req.relocate(PDMBackend(tmp_path))
        req.name = name
        return req

    @staticmethod
    def _repo(candidate: Candidate) -> LockedRepository:
        repo = MagicMock(spec=LockedRepository)
        repo.packages = {("member-a", "0.1.0", None, True): Package(candidate, ["faker"])}
        repo._identify_candidate = lambda can: (
            can.identify(),
            None,
            can.link.url,
            can.req.editable,
        )
        return repo

    def test_named_member_gets_its_path_back(self, tmp_path: Path):
        """`uv` lock files store members as a bare name/version/editable triplet."""
        req = self._member_req(tmp_path)
        # As read back from a `uv` generated lock file: no path, no url
        locked = Candidate(NamedRequirement(name="member-a", editable=True), version="0.1.0")
        repo = self._repo(locked)

        _adapt_locked_members(repo, {"member-a": req})

        (key,) = repo.packages
        package = repo.packages[key]
        assert not package.candidate.req.is_named
        assert package.candidate.req.editable
        assert package.candidate.req.absolute_path == tmp_path / "member-a"
        # `${PROJECT_ROOT}` is expanded by `LockedRepository._identify_candidate`
        assert package.candidate.link.url == "file:///${PROJECT_ROOT}/member-a"
        # The package is re-keyed on its new identity, and its dependencies kept
        assert key == ("member-a", None, "file:///${PROJECT_ROOT}/member-a", True)
        assert package.dependencies == ["faker"]

    def test_path_member_is_left_untouched(self, tmp_path: Path):
        """Lock files keeping the member path need no adaptation."""
        req = self._member_req(tmp_path)
        locked = Candidate(req, version="0.1.0")
        repo = self._repo(locked)
        before = dict(repo.packages)

        _adapt_locked_members(repo, {"member-a": req})

        assert repo.packages == before

    def test_without_members_is_a_noop(self, tmp_path: Path):
        """A project without workspace members is not affected."""
        locked = Candidate(NamedRequirement(name="member-a", editable=True), version="0.1.0")
        repo = self._repo(locked)
        before = dict(repo.packages)

        _adapt_locked_members(repo, {})

        assert repo.packages == before
