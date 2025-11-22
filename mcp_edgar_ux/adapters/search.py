"""
File Search Adapter

Implements FilingSearcher port using ugrep subprocess with fuzzy matching.
"""
import os
import subprocess
from pathlib import Path

from ..core.domain import SearchMatch
from ..core.ports import FilingSearcher


class GrepSearcher(FilingSearcher):
    """File searcher using grep subprocess"""

    def search(
        self,
        file_path: Path,
        pattern: str,
        context_lines: int = 2,
        max_results: int = 20,
        offset: int = 0
    ) -> tuple[list[SearchMatch], int]:
        """Search for pattern in filing, return (matches, total_count)"""
        # Use ugrep with optional fuzzy matching (faster and more forgiving than grep)
        # Set UGREP_FUZZY=0 to disable, UGREP_FUZZY=2 for more permissive matching
        fuzzy_level = int(os.getenv("UGREP_FUZZY", "1"))

        try:
            # Build command args
            args = [
                "ugrep",
                "-E",  # Extended regex
                "-i",  # Case-insensitive
                "-w",  # Whole word matching (prevents "risk" from matching "comprised")
                "-n",  # Line numbers
                f"-C{context_lines}",  # Context lines
            ]

            # Add fuzzy matching if enabled
            if fuzzy_level > 0:
                args.append(f"--fuzzy={fuzzy_level}")

            args.extend([pattern, str(file_path)])

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode not in [0, 1]:  # 0=found, 1=not found, other=error
                raise RuntimeError(f"ugrep failed: {result.stderr}")

            # Parse grep output
            matches = self._parse_grep_output(result.stdout, context_lines)
            total_count = len(matches)

            # Apply offset and max_results
            return matches[offset:offset + max_results], total_count

        except subprocess.TimeoutExpired:
            raise RuntimeError("Search timed out after 30 seconds")

    def count_lines(self, file_path: Path) -> int:
        """Count total lines in file"""
        try:
            result = subprocess.run(
                ["wc", "-l", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"wc failed: {result.stderr}")

            # Parse output: "COUNT FILENAME"
            count_str = result.stdout.split()[0]
            return int(count_str)

        except (subprocess.TimeoutExpired, ValueError) as e:
            raise RuntimeError(f"Failed to count lines: {e}")

    def read_preview(self, file_path: Path, num_lines: int) -> tuple[list[str], int]:
        """Read first N lines with line numbers, return (lines, total_count)"""
        total_lines = self.count_lines(file_path)

        if num_lines == 0:
            return [], total_lines

        lines = []
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f, 1):
                if i > num_lines:
                    break
                # Format like grep -n: "LINE: content" (up to 9999 lines)
                lines.append(f"{i:4d}: {line.rstrip()}")

        return lines, total_lines

    def _parse_grep_output(self, output: str, context_lines: int) -> list[SearchMatch]:
        """Parse grep output into SearchMatch objects"""
        if not output.strip():
            return []

        matches = []
        lines = output.split('\n')

        i = 0
        while i < len(lines):
            if not lines[i].strip():
                i += 1
                continue

            # Check if this is a match line (has line number before ':')
            if ':' in lines[i]:
                parts = lines[i].split(':', 1)
                try:
                    line_num = int(parts[0])
                    line_content = parts[1] if len(parts) > 1 else ''

                    # Extract context before (lines with '-' separator)
                    context_before = []
                    j = i - 1
                    while j >= 0 and len(context_before) < context_lines:
                        if '-' in lines[j]:
                            ctx_parts = lines[j].split('-', 1)
                            if len(ctx_parts) > 1:
                                context_before.insert(0, ctx_parts[1])
                        j -= 1

                    # Extract context after (lines with '-' separator)
                    context_after = []
                    j = i + 1
                    while j < len(lines) and len(context_after) < context_lines:
                        if '-' in lines[j]:
                            ctx_parts = lines[j].split('-', 1)
                            if len(ctx_parts) > 1:
                                context_after.append(ctx_parts[1])
                        else:
                            break
                        j += 1

                    matches.append(SearchMatch(
                        line_number=line_num,
                        line_content=line_content,
                        context_before=context_before,
                        context_after=context_after
                    ))

                except ValueError:
                    pass  # Skip malformed lines

            i += 1

        return matches
