#!/usr/bin/env python3
"""Install registry skills for Claude and Codex, and retire owned stale links.

Missing ``hosts`` defaults to [claude]; Codex uses ~/.agents/skills. Deprecated
links are also cleaned from the legacy ~/.codex/skills location. Only links into
this tools root are replaceable. Unmanaged files, directories and links conflict.

Idempotent. Default = apply to every declared host. Preview with --dry-run.

  python3 scripts/sync-skills.py [--dry-run] [--host claude|codex|all] [--skill NAME ...]

Install kinds:
  dir  -> <host skills>/<name>          symlink to <root>/<source dir>
  file -> <host skills>/<name>/SKILL.md symlink to <root>/<source SKILL.md>
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
CLAUDE_SKILLS = Path.home() / ".claude" / "skills"
CODEX_SKILLS = Path.home() / ".agents" / "skills"
LEGACY_CODEX_SKILLS = Path.home() / ".codex" / "skills"
HOSTS = ("claude", "codex")


def load_registry() -> dict:
    with open(REGISTRY, encoding="utf-8") as f:
        return yaml.safe_load(f)


def skill_hosts(skill: dict) -> list[str]:
    hosts = skill.get("hosts", ["claude"])
    if not isinstance(hosts, list) or not hosts or any(h not in HOSTS for h in hosts):
        raise ValueError("hosts must be a nonempty list containing claude and/or codex")
    if len(hosts) != len(set(hosts)):
        raise ValueError("hosts must not contain duplicates")
    return hosts


def host_dirs(host: str = "all") -> dict[str, Path]:
    return {h: p for h, p in (("claude", CLAUDE_SKILLS), ("codex", CODEX_SKILLS))
            if host == "all" or h == host}


def stale_dirs(host: str = "all") -> dict[str, Path]:
    dirs = host_dirs(host)
    if host in ("all", "codex"):
        dirs["codex legacy"] = LEGACY_CODEX_SKILLS
    return dirs


def valid_name(name: object) -> bool:
    # Project prefixes may contain uppercase letters and underscores. A name
    # must still be a single safe path component, never an escape from skills/.
    return (isinstance(name, str) and bool(name) and name not in (".", "..")
            and "/" not in name and "\\" not in name and "\x00" not in name)


def link_destination(link: Path) -> Path:
    return (link.parent / os.readlink(link)).resolve()


def points_into_root(link: Path) -> bool:
    try:
        link_destination(link).relative_to(ROOT.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def owned_wrapper(path: Path) -> bool:
    return (not path.is_symlink() and path.is_dir()
            and (path / "SKILL.md").is_symlink()
            and points_into_root(path / "SKILL.md"))


def present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def install_skill(skill: dict, dry: bool, log: list, host: str = "claude") -> bool:
    name = skill["name"]
    label = f"{name} [{host}]"
    if not valid_name(name):
        log.append(f"  ✗ {label}: name must be a single path component")
        return False
    scope = skill.get("scope")
    if scope and scope != "global":
        log.append(f"  ~ {label}: scope={scope} (project-local) — skipped")
        return True
    source = (ROOT / skill["source"]).resolve()
    kind = skill.get("install_kind", "dir")
    if not source.exists():
        log.append(f"  ✗ {label}: source missing {source}")
        return False
    if kind not in ("dir", "file"):
        log.append(f"  ✗ {label}: unknown install_kind {kind}")
        return False
    if (kind == "dir" and not source.is_dir()) or (kind == "file" and not source.is_file()):
        log.append(f"  ✗ {label}: source is not a {kind}")
        return False

    base = host_dirs(host)[host]
    entry = base / name
    target = entry if kind == "dir" else entry / "SKILL.md"
    # Never write through an entry symlink for file installs: doing so would
    # modify a source directory rather than the registration wrapper.
    entry_link = kind == "file" and entry.is_symlink()
    if entry_link and not points_into_root(entry):
        log.append(f"  ✗ {label}: conflict at {entry} (unmanaged symlink)")
        return False
    if not entry_link and target.is_symlink() and link_destination(target) == source:
        log.append(f"  = {label} ({kind}) ok")
        return True

    remove_wrapper = False
    if kind == "dir" and present(entry):
        if entry.is_symlink() and points_into_root(entry):
            pass
        elif owned_wrapper(entry) and {p.name for p in entry.iterdir()} == {"SKILL.md"}:
            remove_wrapper = True
        else:
            log.append(f"  ✗ {label}: conflict at {entry} (unmanaged or nonempty directory/file/link)")
            return False
    elif kind == "file" and not entry_link:
        if present(entry) and not owned_wrapper(entry):
            log.append(f"  ✗ {label}: conflict at {entry} (unmanaged wrapper directory/file)")
            return False
        if present(target) and not (target.is_symlink() and points_into_root(target)):
            log.append(f"  ✗ {label}: conflict at {target} (unmanaged file/link)")
            return False

    if dry:
        log.append(f"  + {label} ({kind}) -> would link {target} -> {source}")
        return True
    if entry_link:
        entry.unlink()
    elif remove_wrapper:
        (entry / "SKILL.md").unlink()
        entry.rmdir()
    elif target.is_symlink():
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=(kind == "dir"))
    log.append(f"  + {label} ({kind}) linked -> {source}")
    return True


def remove_stale(dep_id: str, dry: bool, log: list,
                 skills_dir: Path | None = None, host: str = "claude") -> bool:
    """Unlink only owned registrations; never recursively delete a directory."""
    if not valid_name(dep_id):
        log.append(f"  ✗ {dep_id!r} [{host}]: deprecated id must be a single path component")
        return False
    p = (skills_dir if skills_dir is not None else CLAUDE_SKILLS) / dep_id
    if not present(p):
        return True
    direct = p.is_symlink() and points_into_root(p)
    wrapper = owned_wrapper(p)
    if not direct and not wrapper:
        log.append(f"  ! {dep_id} [{host}]: present but not ours — leaving alone")
        return True
    if dry:
        log.append(f"  - {dep_id} [{host}]: would remove stale owned trigger")
        return True
    if direct:
        p.unlink()
    else:
        (p / "SKILL.md").unlink()
        if not any(p.iterdir()):
            p.rmdir()
        else:
            log.append(f"  ! {dep_id} [{host}]: retained wrapper with other files at {p}")
    log.append(f"  - {dep_id} [{host}]: removed stale owned trigger")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--host", choices=(*HOSTS, "all"), default="all")
    ap.add_argument("--skill", action="append", help="install only this registered skill (repeatable)")
    args = ap.parse_args(argv)
    reg = load_registry()
    names = set(args.skill or [])
    unknown = names - {s["name"] for s in reg.get("skills", [])}
    if unknown:
        ap.error("unknown skills: " + ", ".join(sorted(unknown)))
    log: list = ["== install skills =="]
    ok = True
    selected = host_dirs(args.host)
    # Do not use all(generator): a conflict must not prevent later entries from
    # being inspected or installed.
    for skill in reg.get("skills", []):
        if names and skill["name"] not in names:
            continue
        try:
            hosts = skill_hosts(skill)
        except ValueError as exc:
            log.append(f"  ✗ {skill.get('name')}: {exc}")
            ok = False
            continue
        for host in hosts:
            if host in selected:
                try:
                    ok = install_skill(skill, args.dry_run, log, host) and ok
                except (OSError, RuntimeError) as exc:
                    log.append(f"  ✗ {skill['name']} [{host}]: {exc}")
                    ok = False
    log.append("== remove stale triggers ==")
    for dep in reg.get("deprecated", []):
        if names:
            continue
        for host, directory in stale_dirs(args.host).items():
            try:
                ok = remove_stale(dep["id"], args.dry_run, log, directory, host) and ok
            except (OSError, RuntimeError) as exc:
                log.append(f"  ✗ {dep['id']} [{host}]: {exc}")
                ok = False
    print("\n".join(log))
    print("\n" + ("DONE" if ok else "FAILED") + (" (dry-run)" if args.dry_run else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
