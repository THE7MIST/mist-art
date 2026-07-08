from dataclasses import dataclass


@dataclass(frozen=True)
class InvestigationPlan:
    intent: str
    objective: str
    theory: str
    required_artifacts: list[str]
    procedure: list[str]


class QuestionPlanner:
    def plan(self, question: str) -> InvestigationPlan:
        text = question.lower()
        if "zip" in text:
            return InvestigationPlan(
                intent="zip_count",
                objective="Identify and count ZIP archives using file extension and signature verification.",
                theory="ZIP archives normally begin with PK magic bytes and may also appear by extension or carved file signature.",
                required_artifacts=["Filesystem entries", "File signatures", "Hashes"],
                procedure=[
                    "Enumerate visible and recoverable filesystem entries.",
                    "Filter candidate files by .zip extension.",
                    "Validate candidates using ZIP magic bytes.",
                    "Record path, size, hash, and source evidence.",
                    "Cross-check using FTK, Autopsy, and Sleuth Kit commands.",
                ],
            )
        if "filesystem" in text or "file system" in text or "ntfs" in text or "fat" in text:
            return InvestigationPlan(
                intent="filesystem",
                objective="Determine the filesystem type and supporting volume metadata.",
                theory="Filesystem identification is based on partition metadata, superblock/boot sector structures, and tool agreement.",
                required_artifacts=["Partition table", "Volume metadata", "Filesystem statistics"],
                procedure=[
                    "Identify partitions in the evidence image.",
                    "Inspect each volume with filesystem-aware tooling.",
                    "Compare reported filesystem labels across tools.",
                    "Document offsets, block size, and confidence.",
                ],
            )
        if "deleted" in text or "recover" in text:
            return InvestigationPlan(
                intent="deleted_files",
                objective="Find deleted file records and recoverable content.",
                theory="Deleted files may remain in metadata records, unallocated clusters, journal entries, or carved signatures.",
                required_artifacts=["MFT/directory records", "Unallocated space", "Journal entries"],
                procedure=[
                    "Enumerate deleted records from filesystem metadata.",
                    "Search unallocated space for recoverable signatures.",
                    "Validate recovered files with hashes and metadata.",
                    "Separate metadata-only records from content-recoverable files.",
                ],
            )
        if "mac time" in text or "mactime" in text or "created" in text and "modified" in text:
            return InvestigationPlan(
                intent="mac_time",
                objective="Extract Created, Modified, Accessed, and Changed timestamps.",
                theory="MAC times come from filesystem metadata and should be normalized with timezone context.",
                required_artifacts=["MFT metadata", "Filesystem timestamps", "Timeline"],
                procedure=[
                    "Locate the file or artifact requested by the question.",
                    "Extract timestamp fields with metadata-aware tools.",
                    "Normalize timestamps and preserve original timezone assumptions.",
                    "Cross-check with timeline generation.",
                ],
            )
        if "user profile" in text or "profile" in text:
            return InvestigationPlan(
                intent="user_profile",
                objective="Build a user profile from documents, browser data, registry hives, metadata, and timeline activity.",
                theory="User attribution is strongest when independent artifacts converge on names, accounts, paths, and activity patterns.",
                required_artifacts=["User directories", "Registry hives", "Browser history", "Recent files", "Timeline"],
                procedure=[
                    "Enumerate user home/profile directories.",
                    "Extract registry and shellbag activity.",
                    "Review browser history, downloads, and cookies.",
                    "Correlate document metadata and recent file activity.",
                    "Summarize identifiers and confidence.",
                ],
            )
        if "timeline" in text:
            return InvestigationPlan(
                intent="timeline",
                objective="Build a chronological timeline of relevant filesystem and application activity.",
                theory="A forensic timeline correlates timestamps across artifacts to reconstruct activity.",
                required_artifacts=["Filesystem timestamps", "Event logs", "Browser history", "Registry activity"],
                procedure=[
                    "Collect timestamped artifacts from each evidence source.",
                    "Normalize timestamps to a common timezone.",
                    "Sort and de-duplicate events.",
                    "Flag events directly relevant to the question.",
                ],
            )
        if "registry" in text or "sam" in text or "run key" in text or "usb" in text:
            return InvestigationPlan(
                intent="registry",
                objective="Extract registry evidence relevant to the question.",
                theory="Windows registry hives preserve configuration, user activity, persistence, USB, and MRU artifacts.",
                required_artifacts=["SAM", "SYSTEM", "SOFTWARE", "NTUSER.DAT", "USRCLASS.DAT"],
                procedure=[
                    "Locate registry hives in the evidence.",
                    "Run targeted registry parsers.",
                    "Correlate keys with timestamps and user SIDs.",
                    "Document parser output and manual verification path.",
                ],
            )
        if "browser" in text or "chrome" in text or "firefox" in text or "edge" in text:
            return InvestigationPlan(
                intent="browser",
                objective="Extract browser artifacts such as history, downloads, cookies, and saved data references.",
                theory="Browser SQLite databases and cache files preserve user web activity and downloaded evidence.",
                required_artifacts=["Browser SQLite databases", "Download records", "Cookies", "Cache metadata"],
                procedure=[
                    "Locate browser profiles.",
                    "Parse history and downloads databases.",
                    "Normalize timestamps.",
                    "Correlate URLs, filenames, and filesystem artifacts.",
                ],
            )
        if "memory" in text or "process" in text or "dll" in text or "volatility" in text:
            return InvestigationPlan(
                intent="memory",
                objective="Analyze memory evidence for processes, modules, handles, network connections, and suspicious activity.",
                theory="Memory images expose volatile runtime state that may not exist on disk.",
                required_artifacts=["Memory image", "Process list", "Network connections", "Loaded modules"],
                procedure=[
                    "Identify memory profile or symbol requirements.",
                    "Enumerate processes and network connections.",
                    "Inspect suspicious modules, handles, and command lines.",
                    "Correlate volatile findings with disk evidence.",
                ],
            )
        if "password" in text or "encrypted" in text:
            return InvestigationPlan(
                intent="password",
                objective="Identify encrypted files and plan password recovery using evidence-derived candidates.",
                theory="Password recovery is strongest when dictionaries are derived from case-specific metadata and known terms.",
                required_artifacts=["Encrypted archives/documents", "Metadata terms", "Known passwords", "Hashes"],
                procedure=[
                    "Identify encrypted files by signature and metadata.",
                    "Extract hash material with safe tools.",
                    "Build a case-specific candidate dictionary.",
                    "Run approved recovery tools in an isolated worker.",
                ],
            )
        return InvestigationPlan(
            intent="generic",
            objective="Translate the question into required artifacts and produce a reproducible verification plan.",
            theory="Forensic answers should be based on structured evidence, tool output, and independent verification.",
            required_artifacts=["Evidence metadata", "Relevant artifacts", "Tool output"],
            procedure=[
                "Classify the question intent.",
                "Select relevant forensic plugins.",
                "Collect structured evidence.",
                "Generate answer, confidence, GUI steps, and CLI verification.",
            ],
        )


question_planner = QuestionPlanner()
