from __future__ import annotations

from unittest.mock import MagicMock

from packaging.specifiers import SpecifierSet
from pdm.models.requirements import NamedRequirement, Requirement

from pdm_dockerize.commands import _adapt_requirements_for_lockfile


def _make_req(name: str, extras: tuple[str, ...] | None = None) -> Requirement:
    """Create a NamedRequirement with optional extras."""
    return NamedRequirement(name=name, extras=extras)


def _make_project(package_keys: set[str]) -> MagicMock:
    """Create a mock project whose locked repository has the given identity keys.

    ``package_keys`` should contain identity strings such as ``"pkg"`` or
    ``"pkg[extra]"`` — they are expanded into ``CandidateKey`` tuples
    internally.
    """
    locked_repo = MagicMock()
    locked_repo.packages = {(key, None, None, False): MagicMock() for key in package_keys}
    project = MagicMock()
    project.get_locked_repository.return_value = locked_repo
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
