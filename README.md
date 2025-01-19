# REDkitProjectsFixer
 A command line utility for fixing some things in REDkit projects

## Requirements
Python (tested on 3.13) and WolvenKit [7.2.0-nightly.2024-12-13](https://github.com/WolvenKit/WolvenKit-7-nightly/releases/tag/7.2.0-nightly.2024-12-13) or later version

## Usage
Set paths to WolvenKit and your project an run `REDkitProjectsFixer.py` with one of this options:
- `--clean-unused` will clean all unused strings from your `LocalEditorStringDataBaseW3_UTF8_mod_export.csv`
- `--change-id-space your_mod_nexus_id` will clean all unused strings and then change strings ids for the new ones generated in your own id-space (both in `LocalEditorStringDataBaseW3_UTF8_mod_export.csv` and projects files)
- `--assign-audio-and-lipsync` will add `.wem` and `.re` paths to scenes files. Lipsync files must be placed into `<your_project_dir>\speech\en\lipsync`, audio (wem) files must be placed into `<your_project_dir>\speech\en\audio`. All files must have proper names: `<voiceFileName>.re` for lipsync and `<voiceFileName>.wem` for audio (you can see `voiceFileName` in `CStorySceneLine` in your scene or in `VOICEOVER` column in `LocalEditorStringDataBaseW3_UTF8_mod_export.csv`)

#### NOTES:
- `your_mod_nexus_id` is a number from your mod's URL on Nexusmods. E.g. for https://www.nexusmods.com/witcher3/mods/9453 it is 9453
- REDkit Projects Fixer 3-in-1 doesn't change `LocalEditorStringDataBaseW3_UTF8_mod.db`, it changes only exported `.csv`! You can use [Strings DB editor for Redkit](https://www.nexusmods.com/witcher3/mods/9513) to delete all strings and import changed strings from `LocalEditorStringDataBaseW3_UTF8_mod_export.csv`.

![Alt text](https://staticdelivery.nexusmods.com/mods/952/images/10108/10108-1734977722-1912235690.jpeg)

![Alt text](https://staticdelivery.nexusmods.com/mods/952/images/10108/10108-1734977232-279036270.jpeg)

[NexusMods page](https://www.nexusmods.com/witcher3/mods/10108)
