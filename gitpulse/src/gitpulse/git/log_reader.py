"""Git log reading helpers."""

from __future__ import annotations

from datetime import datetime

from gitpulse.git.repository import GitRepository
from gitpulse.models.git_log import GitCommitRecord

FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"


class GitLogReader:
    """Read structured commit records from Git log."""

    def __init__(self, repository: GitRepository) -> None:
        self.repository = repository

    def read(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        authors: list[str] | None = None,
        branches: list[str] | None = None,
        max_count: int = 200,
    ) -> list[GitCommitRecord]:
        refs = branches or ["HEAD"]
        pretty = (
            f"{RECORD_SEPARATOR}%H{FIELD_SEPARATOR}%h{FIELD_SEPARATOR}%an"
            f"{FIELD_SEPARATOR}%ae{FIELD_SEPARATOR}%aI{FIELD_SEPARATOR}%cI"
            f"{FIELD_SEPARATOR}%P{FIELD_SEPARATOR}%s{FIELD_SEPARATOR}%B"
        )
        args = [
            "log",
            *refs,
            f"--since={date_from.isoformat()}",
            f"--until={date_to.isoformat()}",
            f"--max-count={max_count}",
            f"--format={pretty}",
            "--numstat",
            "-z",
        ]
        output = self.repository.runner.run(args).stdout
        records = self._parse(output)
        if authors:
            wanted = {author.lower() for author in authors}
            records = [record for record in records if record.author_email.lower() in wanted]
        return records[:max_count]

    def _parse(self, output: str) -> list[GitCommitRecord]:
        chunks = [chunk for chunk in output.split(RECORD_SEPARATOR) if chunk.strip("\0\n")]
        return [self._parse_record(chunk) for chunk in chunks]

    def _parse_record(self, chunk: str) -> GitCommitRecord:
        header, _, rest = chunk.partition("\n")
        fields = header.strip("\0\n").split(FIELD_SEPARATOR, 8)
        if len(fields) < 9:
            raise ValueError("invalid git log record")
        body_and_stats = fields[8] + ("\n" + rest if rest else "")
        body, changed_files, insertions, deletions = self._parse_body_and_stats(body_and_stats)
        return GitCommitRecord(
            commit_hash=fields[0],
            short_hash=fields[1],
            author_name=fields[2],
            author_email=fields[3],
            authored_at=datetime.fromisoformat(fields[4]),
            committed_at=datetime.fromisoformat(fields[5]),
            parents=[parent for parent in fields[6].split() if parent],
            subject=fields[7],
            body=body,
            changed_files=changed_files,
            insertions=insertions,
            deletions=deletions,
        )

    def _parse_body_and_stats(self, value: str) -> tuple[str, list[str], int, int]:
        body_lines: list[str] = []
        changed_files: list[str] = []
        insertions = 0
        deletions = 0
        for raw_line in value.replace("\0", "\n").splitlines():
            line = raw_line.strip("\n")
            parts = line.split("\t")
            if len(parts) >= 3 and (parts[0].isdigit() or parts[0] == "-") and (parts[1].isdigit() or parts[1] == "-"):
                insertions += 0 if parts[0] == "-" else int(parts[0])
                deletions += 0 if parts[1] == "-" else int(parts[1])
                changed_files.append(parts[-1].replace("\\", "/"))
            else:
                body_lines.append(line)
        body = "\n".join(line for line in body_lines).strip()
        return body, changed_files, insertions, deletions

