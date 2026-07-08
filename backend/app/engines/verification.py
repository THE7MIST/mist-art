from app.schemas import GuiWorkflow, VerificationStep


class VerificationEngine:
    def gui_workflows(self, intent: str) -> list[GuiWorkflow]:
        base_ftk = [
            "Open FTK Imager.",
            "Select File > Add Evidence Item.",
            "Choose Image File and select the mounted case evidence.",
            "Expand the evidence tree and inspect the relevant volume or folder.",
        ]
        base_autopsy = [
            "Create or open the Autopsy case.",
            "Select Add Data Source and choose Disk Image or VM File.",
            "Wait for ingest modules to complete.",
            "Open Data Sources and inspect the relevant artifact view.",
        ]
        if intent == "zip_count":
            return [
                GuiWorkflow(
                    tool="FTK Imager",
                    steps=base_ftk + [
                        "Use the file list filter or sort by extension.",
                        "Confirm ZIP candidates by viewing the file header or properties.",
                    ],
                    expected_observation="ZIP candidates show .zip extension and PK file header where available.",
                ),
                GuiWorkflow(
                    tool="Autopsy",
                    steps=base_autopsy + [
                        "Open Views > File Types > By Extension.",
                        "Select ZIP or Archives and record paths and counts.",
                    ],
                    expected_observation="Autopsy lists ZIP/archive files with paths and metadata.",
                ),
            ]
        if intent == "filesystem":
            return [
                GuiWorkflow(
                    tool="FTK Imager",
                    steps=base_ftk + ["Select the volume root and review properties for filesystem metadata."],
                    expected_observation="Volume properties show the filesystem type and volume details.",
                ),
                GuiWorkflow(
                    tool="Autopsy",
                    steps=base_autopsy + ["Open Data Source Summary and review volume information."],
                    expected_observation="Autopsy reports partition and filesystem information.",
                ),
            ]
        return [
            GuiWorkflow(
                tool="FTK Imager",
                steps=base_ftk + ["Navigate to the artifact path identified in the report."],
                expected_observation="The relevant artifact is visible with metadata matching the report.",
            ),
            GuiWorkflow(
                tool="Autopsy",
                steps=base_autopsy + ["Use keyword search or artifact views to locate the reported item."],
                expected_observation="The artifact view contains the same evidence values reported by MIST.",
            ),
        ]

    def cli_steps(self, intent: str, image_path_hint: str = "evidence.dd") -> list[VerificationStep]:
        if intent == "zip_count":
            return [
                VerificationStep(
                    method="Sleuth Kit extension enumeration",
                    command=f"fls -r -p {image_path_hint} | grep -i '\\.zip$'",
                    expected_output="One line per visible ZIP candidate.",
                    notes="Use the correct partition offset with -o when the image contains a partition table.",
                ),
                VerificationStep(
                    method="Sleuth Kit content extraction",
                    command=f"icat {image_path_hint} <inode> | xxd -l 8",
                    expected_output="ZIP files normally begin with 50 4b 03 04, 50 4b 05 06, or 50 4b 07 08.",
                ),
            ]
        if intent == "filesystem":
            return [
                VerificationStep(
                    method="Partition listing",
                    command=f"mmls {image_path_hint}",
                    expected_output="Partition table with start sectors and partition descriptions.",
                ),
                VerificationStep(
                    method="Filesystem statistics",
                    command=f"fsstat -o <start_sector> {image_path_hint}",
                    expected_output="Filesystem type, metadata range, block size, and volume details.",
                ),
            ]
        if intent == "memory":
            return [
                VerificationStep(
                    method="Volatility process listing",
                    command="vol -f memory.raw windows.pslist",
                    expected_output="Process table with PID, PPID, image name, offsets, and timestamps.",
                )
            ]
        if intent == "registry":
            return [
                VerificationStep(
                    method="RegRipper targeted hive parsing",
                    command="rip.pl -r NTUSER.DAT -p recentdocs",
                    expected_output="RecentDocs or relevant plugin output for the selected hive.",
                )
            ]
        return [
            VerificationStep(
                method="Sleuth Kit recursive listing",
                command=f"fls -r -p {image_path_hint}",
                expected_output="Recursive filesystem listing for manual confirmation.",
            )
        ]


verification_engine = VerificationEngine()
