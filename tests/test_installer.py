from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from installer.destinations import Scheme
from installer.records import RecordEntry

from pdm_dockerize.installer import DockerizeUvSynchronizer, FilteringDestination

# ---------------------------------------------------------------------------
# FilteringDestination
# ---------------------------------------------------------------------------


@pytest.fixture
def scheme_dict(tmp_path: Path) -> dict[str, str]:
    """Minimal scheme dict required by InstallDestination."""
    dirs = {
        "purelib": str(tmp_path / "purelib"),
        "platlib": str(tmp_path / "platlib"),
        "headers": str(tmp_path / "headers"),
        "scripts": str(tmp_path / "scripts"),
        "data": str(tmp_path / "data"),
    }
    for d in dirs.values():
        Path(d).mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture
def destination(scheme_dict: dict[str, str]) -> FilteringDestination:
    """A FilteringDestination with include=["*"] and no excludes."""
    return FilteringDestination(
        scheme_dict=scheme_dict,
        interpreter="/usr/bin/python3",
        script_kind="posix",
        include=["*"],
        exclude=[],
    )


class TestFilteringDestinationInit:
    def test_default_link_method_is_copy(self, scheme_dict: dict[str, str]):
        dest = FilteringDestination(
            scheme_dict=scheme_dict,
            interpreter="/usr/bin/python3",
            script_kind="posix",
        )
        assert dest.link_method == "copy"

    def test_include_exclude_default_to_empty(self, scheme_dict: dict[str, str]):
        dest = FilteringDestination(
            scheme_dict=scheme_dict,
            interpreter="/usr/bin/python3",
            script_kind="posix",
        )
        assert dest.include == []
        assert dest.exclude == []

    def test_include_exclude_stored(self, scheme_dict: dict[str, str]):
        dest = FilteringDestination(
            scheme_dict=scheme_dict,
            interpreter="/usr/bin/python3",
            script_kind="posix",
            include=["foo", "bar"],
            exclude=["baz"],
        )
        assert dest.include == ["foo", "bar"]
        assert dest.exclude == ["baz"]

    def test_none_include_exclude_becomes_empty(self, scheme_dict: dict[str, str]):
        dest = FilteringDestination(
            scheme_dict=scheme_dict,
            interpreter="/usr/bin/python3",
            script_kind="posix",
            include=None,
            exclude=None,
        )
        assert dest.include == []
        assert dest.exclude == []


@dataclass
class WriteScriptCase:
    id: str
    include: list[str]
    exclude: list[str]
    script_name: str
    should_install: bool


WRITE_SCRIPT_CASES = (
    WriteScriptCase(
        id="included-by-wildcard",
        include=["*"],
        exclude=[],
        script_name="faker",
        should_install=True,
    ),
    WriteScriptCase(
        id="included-by-exact-name",
        include=["faker"],
        exclude=[],
        script_name="faker",
        should_install=True,
    ),
    WriteScriptCase(
        id="not-included",
        include=["other"],
        exclude=[],
        script_name="faker",
        should_install=False,
    ),
    WriteScriptCase(
        id="empty-include-blocks-all",
        include=[],
        exclude=[],
        script_name="faker",
        should_install=False,
    ),
    WriteScriptCase(
        id="included-then-excluded",
        include=["*"],
        exclude=["faker"],
        script_name="faker",
        should_install=False,
    ),
    WriteScriptCase(
        id="included-not-excluded-by-pattern",
        include=["*"],
        exclude=["py*"],
        script_name="faker",
        should_install=True,
    ),
    WriteScriptCase(
        id="excluded-by-pattern",
        include=["*"],
        exclude=["py*"],
        script_name="pytest",
        should_install=False,
    ),
    WriteScriptCase(
        id="include-pattern-match",
        include=["fa*"],
        exclude=[],
        script_name="faker",
        should_install=True,
    ),
    WriteScriptCase(
        id="include-pattern-no-match",
        include=["fa*"],
        exclude=[],
        script_name="black",
        should_install=False,
    ),
)


class TestFilteringDestinationWriteScript:
    @pytest.mark.parametrize(
        "case",
        [pytest.param(case, id=case.id) for case in WRITE_SCRIPT_CASES],
    )
    @patch("pdm.installers.installers.InstallDestination.write_script")
    def test_write_script_filtering(
        self, mock_write_script: MagicMock, case: WriteScriptCase, scheme_dict: dict[str, str]
    ):
        real_record = RecordEntry("scripts/somescript", None, None)
        mock_write_script.return_value = real_record

        dest = FilteringDestination(
            scheme_dict=scheme_dict,
            interpreter="/usr/bin/python3",
            script_kind="posix",
            include=case.include,
            exclude=case.exclude,
        )

        result = dest.write_script(case.script_name, "some.module", "main", "console")

        if case.should_install:
            mock_write_script.assert_called_once_with(
                case.script_name, "some.module", "main", "console"
            )
            assert result is real_record
        else:
            mock_write_script.assert_not_called()
            assert result.path == ""
            assert result.hash_ is None
            assert result.size is None


class TestFilteringDestinationFinalizeInstallation:
    @patch("pdm.installers.installers.InstallDestination.finalize_installation")
    def test_filters_empty_records(
        self, mock_finalize: MagicMock, destination: FilteringDestination
    ):
        valid_record_1 = RecordEntry("purelib/module.py", None, 100)
        empty_record = RecordEntry("", None, None)
        valid_record_2 = RecordEntry("purelib/other.py", None, 200)

        records: list[tuple[Scheme, RecordEntry]] = [
            (Scheme("purelib"), valid_record_1),
            (Scheme("scripts"), empty_record),
            (Scheme("purelib"), valid_record_2),
        ]

        destination.finalize_installation(Scheme("purelib"), "pkg-1.0.dist-info/RECORD", records)

        mock_finalize.assert_called_once()
        passed_records = mock_finalize.call_args[0][2]
        assert len(passed_records) == 2
        assert all(record.path for _, record in passed_records)

    @patch("pdm.installers.installers.InstallDestination.finalize_installation")
    def test_all_empty_records_produces_empty_list(
        self, mock_finalize: MagicMock, destination: FilteringDestination
    ):
        records: list[tuple[Scheme, RecordEntry]] = [
            (Scheme("scripts"), RecordEntry("", None, None)),
            (Scheme("scripts"), RecordEntry("", None, None)),
        ]

        destination.finalize_installation(Scheme("purelib"), "pkg-1.0.dist-info/RECORD", records)

        mock_finalize.assert_called_once()
        passed_records = mock_finalize.call_args[0][2]
        assert len(passed_records) == 0

    @patch("pdm.installers.installers.InstallDestination.finalize_installation")
    def test_all_valid_records_kept(
        self, mock_finalize: MagicMock, destination: FilteringDestination
    ):
        records: list[tuple[Scheme, RecordEntry]] = [
            (Scheme("purelib"), RecordEntry("purelib/a.py", None, 100)),
            (Scheme("purelib"), RecordEntry("purelib/b.py", None, 200)),
        ]

        destination.finalize_installation(Scheme("purelib"), "pkg-1.0.dist-info/RECORD", records)

        mock_finalize.assert_called_once()
        passed_records = mock_finalize.call_args[0][2]
        assert len(passed_records) == 2


# ---------------------------------------------------------------------------
# DockerizeUvSynchronizer
# ---------------------------------------------------------------------------


def _make_named_candidate(name: str, version: str, pinned_line: str) -> MagicMock:
    """Create a mock candidate representing a named (registry) package."""
    candidate = MagicMock()
    candidate.req.is_named = True
    candidate.version = version
    pinned = MagicMock()
    pinned.as_line.return_value = pinned_line
    candidate.req.as_pinned_version.return_value = pinned
    return candidate


def _make_url_candidate(line: str) -> MagicMock:
    """Create a mock candidate representing a file/VCS/URL requirement."""
    candidate = MagicMock()
    candidate.req.is_named = False
    candidate.req.as_line.return_value = line
    return candidate


def _make_uv_synchronizer(
    tmp_path: Path,
    candidates: dict[str, MagicMock] | None = None,
    include_bins: str | list[str] | None = None,
    exclude_bins: str | list[str] | None = None,
    dry_run: bool = False,
    sources: list | None = None,
) -> DockerizeUvSynchronizer:
    """Create a DockerizeUvSynchronizer with mocked project/environment."""
    project = MagicMock()
    dockerize_settings: dict = {}
    if include_bins is not None:
        dockerize_settings["include_bins"] = include_bins
    if exclude_bins is not None:
        dockerize_settings["exclude_bins"] = exclude_bins
    project.pyproject.settings.get.side_effect = lambda key, default=None: (
        dockerize_settings if key == "dockerize" else default
    )
    project.core.uv_cmd = ["uv"]
    project.sources = sources or []
    project.root = tmp_path

    environment = MagicMock()
    environment.packages_path = tmp_path / "packages"
    environment.interpreter.executable = "/usr/bin/python3"

    return DockerizeUvSynchronizer(
        project=project,
        environment=environment,
        candidates=candidates or {},  # type: ignore[arg-type]
        dry_run=dry_run,
    )


class TestBuildPackageSpecs:
    def test_named_packages(self, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
            "requests": _make_named_candidate("requests", "2.31.0", "requests==2.31.0"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates)
        specs = sync._build_package_specs()

        assert "Faker==18.0.0" in specs
        assert "requests==2.31.0" in specs

    def test_url_requirement(self, tmp_path: Path):
        candidates = {
            "mypkg": _make_url_candidate("git+https://github.com/user/repo.git@main"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates)
        specs = sync._build_package_specs()

        assert specs == ["git+https://github.com/user/repo.git@main"]

    def test_mixed_requirements(self, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
            "mypkg": _make_url_candidate("/path/to/local/pkg"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates)
        specs = sync._build_package_specs()

        assert len(specs) == 2
        assert "Faker==18.0.0" in specs
        assert "/path/to/local/pkg" in specs

    def test_empty_candidates(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, candidates={})
        assert sync._build_package_specs() == []


class TestBuildCommand:
    def test_basic_command_structure(self, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates)
        cmd = sync._build_command("/target/lib")

        assert cmd[:3] == ["uv", "pip", "install"]
        assert "--target" in cmd
        assert cmd[cmd.index("--target") + 1] == "/target/lib"
        assert "-p" in cmd
        assert cmd[cmd.index("-p") + 1] == "/usr/bin/python3"
        assert "--reinstall" in cmd
        assert "Faker==18.0.0" in cmd

    def test_first_index_source(self, tmp_path: Path):
        source = MagicMock()
        source.type = "index"
        source.url_with_credentials = "https://pypi.org/simple/"

        sync = _make_uv_synchronizer(tmp_path, sources=[source])
        cmd = sync._build_command("/target/lib")

        assert "--index-url" in cmd
        assert cmd[cmd.index("--index-url") + 1] == "https://pypi.org/simple/"

    def test_extra_index_sources(self, tmp_path: Path):
        source1 = MagicMock()
        source1.type = "index"
        source1.url_with_credentials = "https://pypi.org/simple/"

        source2 = MagicMock()
        source2.type = "index"
        source2.url_with_credentials = "https://private.pypi.org/simple/"

        sync = _make_uv_synchronizer(tmp_path, sources=[source1, source2])
        cmd = sync._build_command("/target/lib")

        assert "--index-url" in cmd
        assert cmd[cmd.index("--index-url") + 1] == "https://pypi.org/simple/"
        assert "--extra-index-url" in cmd
        assert cmd[cmd.index("--extra-index-url") + 1] == "https://private.pypi.org/simple/"

    def test_find_links_source(self, tmp_path: Path):
        source = MagicMock()
        source.type = "find_links"
        source.url_with_credentials = "/path/to/wheels"

        sync = _make_uv_synchronizer(tmp_path, sources=[source])
        cmd = sync._build_command("/target/lib")

        assert "--find-links" in cmd
        assert cmd[cmd.index("--find-links") + 1] == "/path/to/wheels"

    def test_url_with_secret_attribute(self, tmp_path: Path):
        url = MagicMock()
        url.secret = "https://token@private.pypi.org/simple/"

        source = MagicMock()
        source.type = "index"
        source.url_with_credentials = url

        sync = _make_uv_synchronizer(tmp_path, sources=[source])
        cmd = sync._build_command("/target/lib")

        assert "--index-url" in cmd
        assert cmd[cmd.index("--index-url") + 1] == "https://token@private.pypi.org/simple/"


class TestProcessScripts:
    def test_moves_matching_scripts(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*")

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        script = src_bin / "faker"
        script.write_text("#!/usr/bin/env python\nprint('faker')")

        sync._process_scripts(lib_path, bin_path)

        assert (bin_path / "faker").is_file()
        assert not src_bin.exists()  # cleaned up

    def test_moved_scripts_preserve_permissions(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*")

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        script = src_bin / "myscript"
        script.write_text("#!/usr/bin/env python\nprint('hello')")
        script.chmod(0o755)

        sync._process_scripts(lib_path, bin_path)

        dest = bin_path / "myscript"
        assert dest.is_file()
        mode = dest.stat().st_mode
        assert mode & stat.S_IXUSR  # executable bit is preserved from source

    def test_excluded_scripts_not_moved(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*", exclude_bins=["faker"])

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        (src_bin / "faker").write_text("#!/usr/bin/env python")
        (src_bin / "black").write_text("#!/usr/bin/env python")

        sync._process_scripts(lib_path, bin_path)

        assert not (bin_path / "faker").exists()
        assert (bin_path / "black").is_file()

    def test_not_included_scripts_not_moved(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins=["faker"])

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        (src_bin / "faker").write_text("#!/usr/bin/env python")
        (src_bin / "black").write_text("#!/usr/bin/env python")

        sync._process_scripts(lib_path, bin_path)

        assert (bin_path / "faker").is_file()
        assert not (bin_path / "black").exists()

    def test_no_bin_dir_is_noop(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*")

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        lib_path.mkdir(parents=True)

        sync._process_scripts(lib_path, bin_path)

        assert not bin_path.exists()

    def test_skips_directories(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*")

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        (src_bin / "subdir").mkdir()
        script = src_bin / "myscript"
        script.write_text("#!/usr/bin/env python")

        sync._process_scripts(lib_path, bin_path)

        assert (bin_path / "myscript").is_file()
        assert not (bin_path / "subdir").exists()

    def test_cleans_up_lib_bin(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*")

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        (src_bin / "script").write_text("#!/usr/bin/env python")

        sync._process_scripts(lib_path, bin_path)

        assert not src_bin.exists()
        assert lib_path.exists()  # parent still exists

    def test_empty_include_moves_nothing(self, tmp_path: Path):
        """With empty include list, no scripts match."""
        sync = _make_uv_synchronizer(tmp_path)  # default: no include_bins

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        (src_bin / "script").write_text("#!/usr/bin/env python")

        sync._process_scripts(lib_path, bin_path)

        assert not (bin_path / "script").exists()

    def test_pattern_filtering(self, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, include_bins="*", exclude_bins=["py*"])

        lib_path = tmp_path / "lib"
        bin_path = tmp_path / "bin"
        src_bin = lib_path / "bin"
        src_bin.mkdir(parents=True)

        (src_bin / "pytest").write_text("#!/usr/bin/env python")
        (src_bin / "pygmentize").write_text("#!/usr/bin/env python")
        (src_bin / "faker").write_text("#!/usr/bin/env python")
        (src_bin / "black").write_text("#!/usr/bin/env python")

        sync._process_scripts(lib_path, bin_path)

        assert not (bin_path / "pytest").exists()
        assert not (bin_path / "pygmentize").exists()
        assert (bin_path / "faker").is_file()
        assert (bin_path / "black").is_file()


class TestSynchronize:
    @patch("pdm_dockerize.installer.subprocess.run")
    def test_empty_candidates_skips_install(self, mock_run: MagicMock, tmp_path: Path):
        sync = _make_uv_synchronizer(tmp_path, candidates={})

        sync.synchronize()

        mock_run.assert_not_called()

    @patch("pdm_dockerize.installer.subprocess.run")
    def test_dry_run_does_not_call_subprocess(self, mock_run: MagicMock, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates, dry_run=True)

        sync.synchronize()

        mock_run.assert_not_called()

    @patch("pdm_dockerize.installer.subprocess.run")
    def test_synchronize_calls_uv(self, mock_run: MagicMock, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates, include_bins="*")

        sync.synchronize()

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "uv" in cmd
        assert "pip" in cmd
        assert "install" in cmd
        assert mock_run.call_args[1]["check"] is True

    @patch("pdm_dockerize.installer.subprocess.run")
    def test_synchronize_creates_lib_dir(self, mock_run: MagicMock, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates)

        sync.synchronize()

        lib_path = tmp_path / "packages" / "lib"
        assert lib_path.is_dir()

    @patch("pdm_dockerize.installer.subprocess.run")
    def test_synchronize_processes_scripts_after_install(self, mock_run: MagicMock, tmp_path: Path):
        candidates = {
            "faker": _make_named_candidate("faker", "18.0.0", "Faker==18.0.0"),
        }
        sync = _make_uv_synchronizer(tmp_path, candidates=candidates, include_bins="*")

        # Simulate uv creating a script in lib/bin/
        packages_path = tmp_path / "packages"
        lib_bin = packages_path / "lib" / "bin"

        def fake_uv_install(*args, **kwargs):
            lib_bin.mkdir(parents=True, exist_ok=True)
            script = lib_bin / "faker"
            script.write_text("#!/usr/bin/env python\nprint('faker')")

        mock_run.side_effect = fake_uv_install

        sync.synchronize()

        # Script should have been moved from lib/bin/ to bin/
        assert (packages_path / "bin" / "faker").is_file()
        assert not lib_bin.exists()
