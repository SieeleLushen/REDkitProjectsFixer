import os
import subprocess
import time
import shutil
import colorama
import hashlib
import sys

log_file = ''
failed_files = []

# ---------- !!! SET YOUR PATHS HERE !!! ---------- 

# Path to WolvenKit.CLI.exe
# WolvenKit 7.2.0-nightly.2024-12-13 is required
# https://github.com/WolvenKit/WolvenKit-7-nightly/releases/tag/7.2.0-nightly.2024-12-13
WolvenKit_path = r'F:\WolvenKit (TW3) Nightly\WolvenKit.CLI.exe' 

# Path to your REDkit project directory - a folder where "workspace", "LocalEditorStringDataBaseW3_UTF8_mod.db" and other stuff are placed
redkit_mod_path = r'D:\The Spider and the Wolf\dlc'

# ------------------------------------------------- 

# For cmd coloring
def cmd_color(color, text):
    if color == 'red':
        return(f'\u001b[38;2;255;0;0m{text}\u001b[0m')
    elif color == 'green':
        return(f'\u001b[38;2;0;255;0m{text}\u001b[0m')
    elif color == 'yellow':
        return(f'\u001b[38;2;255;255;0m{text}\u001b[0m')
    elif color == 'white':
        return text
        

# Extraction LocalizedString ids from file
def extractStrId(filename):  
    props = open(redkit_mod_path + f'\\RedkitFixer_backups\\_tmp\\{filename}', encoding='utf-8').readlines()
    str_values = []
    
    for i in range(len(props)):
        if props[i].strip() == '"_type": "LocalizedString",': 
            str_values.append(props[i + 1][props[i + 1].find(":") + 1:].strip())
    
    return str_values


# Extraction ids from files
def getStrIdsFromFiles(path, scenes_only=False, files_counter=[]):

    global WolvenKit_path
    global log_file
    global failed_files
    
    str_ids = {}
    
    if scenes_only:
        exts = ['.w2scene']
    else:
        exts = ['.w2scene', '.journal', '.w2ent']
    
    if len(files_counter) == 0:
        files_counter.append(countFiles(path, exts)) # total number
        files_counter.append(1) # counter
       
    for dr in os.listdir(path):
        abs_path = os.path.join(path, dr)
        
        if os.path.isfile(abs_path): 
            ext = abs_path[abs_path.rfind('.'):]
            
            if ext in exts:
                showLogLine(f'[{files_counter[1]}/{files_counter[0]}] ' + abs_path.replace(f'{redkit_mod_path}\\workspace\\', ""), 'white')
                files_counter[1] += 1 # counter
                
                process = subprocess.Popen([WolvenKit_path, "--cr2w2json", "--input", abs_path,
                                            "--output", f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(abs_path)}.json'],
                                           stdout=log_file, stderr=log_file)
                process.wait()  
                
                if process.returncode != 0:
                    showLogLine('WOLVENKIT cr2w2json CONVERTATION ERROR!!! FILE WAS SKIPPED', 'red')
                    failed_files.append(abs_path)
                    
                else:
                    
                    if os.path.exists(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(abs_path)}.json'):
                        tmp = extractStrId(f'{hash(abs_path)}.json')

                        if len(tmp) == 0:
                            os.remove(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(abs_path)}.json') 
                        else:
                            str_ids.update({abs_path: tmp})
                            
                    else: # Wkit unsupported version handler
                        showLogLine('WOLVENKIT cr2w2json CONVERTATION ERROR!!! FILE WAS SKIPPED', 'red')
                        failed_files.append(abs_path)
                        
        else:
            str_ids.update(getStrIdsFromFiles(abs_path, scenes_only, files_counter))

    return str_ids
    
    
# Reading lines from REDkit strings dump
def getStringsFromDump(path):
      
    db_lines = open(path, encoding='utf-8').readlines()
    incompleted_line = []
    
    Redkit_db = []
    
    for i in range(1, len(db_lines)):
        db_lines[i] = db_lines[i][:-1].split(';')

        # incompleted lines appear when \n appeared in line for some reason and have to be merged to get completed line
        if len(incompleted_line) > 0: # join line with previous
            incompleted_line[-1] = incompleted_line[-1].strip() + ' ' + db_lines[i][0] # possible double space fix
            db_lines[i] = incompleted_line + db_lines[i][1:]
            incompleted_line = db_lines[i]

        if len(db_lines[i]) == 22:
            incompleted_line = []
            Redkit_db.append(db_lines[i])
    
    return Redkit_db
    
    
# Cleaning DB resource path
def getPath(line):
    if '\\' not in line:
        return '' # no path
    
    line = line[line.find(' ') + 1:].replace('"', '')
    
    return line
   
   
# Validation DB string via ids from files
def validateStrings(dump, files_strings):
    
    extracted_strings = set()
    
    for id_set in files_strings.values():
        extracted_strings.update(id_set)
    
    totalnum = len(dump)
    
    local_failed_resources = [filepath.replace(f'{redkit_mod_path}\\workspace\\', '') for filepath in failed_files]
    
    # validated if: (1) not empty KEY -> item from xml def; (2) ID was in files; (3) resorce path is in not converted & processed files (to not corrupt the mod) and NOT VANILLA RANGE (1300000)
    for i in range(totalnum):   
        if int(dump[i][0]) < 1300000: 
            dump[i].append(False)
            showLogLine(f'[{i}/{totalnum}] {dump[i][0]} is vanilla id', 'white')     
        elif (dump[i][4] != '') | (dump[i][0] in extracted_strings):
            dump[i].append(True)
            showLogLine(f'[{i}/{totalnum}] {dump[i][0]} is validated', 'white')
        elif getPath(dump[i][1]) in local_failed_resources: 
            dump[i].append(True)
            showLogLine(f'[{i}/{totalnum}] {dump[i][0]} is used by unconverted resources', 'white')
        else:
            dump[i].append(False)
            showLogLine(f'[{i}/{totalnum}] {dump[i][0]} will be deleted', 'white')
    
    return dump
    

# Assigning new ids for strings in dump
def reassignIdsDump(dump, idspace_new):
    
    dump = [data[:-1] for data in dump if data[-1] == True]
         
    iditer = 0     
    totalnum = len(dump)
    
    local_failed_resources = [filepath.replace(f'{redkit_mod_path}\\workspace\\', '') for filepath in failed_files]
    
    for i in range(totalnum):
    
        if getPath(dump[i][1]) in local_failed_resources: # if in not converted & processed files - leave as is
            dump[i].append(dump[i][0])
            showLogLine(f'[{i}/{totalnum}] {dump[i][0]} from skipped files => left as is', 'white')
        
        else:
            dump[i].append(str(idspace_new  + iditer))
            
            showLogLine(f'[{i}/{totalnum}] {dump[i][0]} -> {idspace_new  + iditer}', 'white')
            
            if dump[i][3] != '': # VOICEOVER
                dump[i][3] = dump[i][3].replace(dump[i][0], dump[i][-1])
        
            iditer += 1   
               
    return dump
 
 
# Safe id replacing  
def replaceId(line, old_id, id_dict):

    if old_id not in id_dict.keys():
        showLogLine(f'{old_id} not in StringDB_export. Probably vanilla line.', 'yellow')        
        return line
        
    return line.replace(old_id, id_dict[old_id])
    
    
# Changing strings ids in files
def changeIdsInFiles(dump, files):

    global log_file
    
    new_ids = {data[0]: data[-1] for data in dump}
    files = files.keys()
    
    totalnum = len(files)
    counter = 1
    
    for filename in files:
        showLogLine(f'[{counter}/{totalnum}] ' + filename.replace(f'{redkit_mod_path}\\workspace\\', ""), 'white')
        counter += 1
        
        lines = open(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(filename)}.json', encoding='utf-8').readlines()
        
        for i in range(len(lines)):
            if 'LocalizedString' in lines[i]:
                id_val = lines[i + 1].replace('"_value":', '').replace('\n', '').strip()
                lines[i + 1] = replaceId(lines[i + 1], id_val, new_ids)
                
            elif 'voiceFileName' in lines[i]:
                id_val = lines[i + 2][lines[i + 2].rfind('_') + 1:].replace('"', '').replace('\n', '')
                lines[i + 2] = replaceId(lines[i + 2], id_val, new_ids)
                
            elif 'overriddenLipsyncFilePath' in lines[i]:
                actor_prefix = lines[i + 2][lines[i + 2].rfind('\\') + 1:].replace('\n', '').strip()
                id_val = actor_prefix[actor_prefix.rfind('_') + 1:].replace('.re', '').replace('"', '').strip()
                actor_prefix = actor_prefix[:actor_prefix.rfind('_')]
                lines[i + 2] = replaceId(lines[i + 2], id_val, new_ids)
                
                if os.path.exists(f'{redkit_mod_path}\\speech\\en\\lipsync\\{actor_prefix}_{new_ids[id_val]}.re'): # already renamed
                    showLogLine(f'speech\\en\\audio\\{actor_prefix}_{id_val}.re already renamed', 'yellow')
                elif os.path.exists(f'{redkit_mod_path}\\speech\\en\\lipsync\\{actor_prefix}_{id_val}.re'):
                    os.rename(f'{redkit_mod_path}\\speech\\en\\lipsync\\{actor_prefix}_{id_val}.re',
                              f'{redkit_mod_path}\\speech\\en\\lipsync\\{actor_prefix}_{new_ids[id_val]}.re')
                else:
                    showLogLine(f'RENAMING FILE ERROR!!! speech\\en\\audio\\{actor_prefix}_{id_val}.re DOESN\'T EXIST', 'yellow')
                    
            elif 'overriddenAudioFilePath' in lines[i]:
                actor_prefix = lines[i + 2][lines[i + 2].rfind('\\') + 1:].replace('\n', '').strip()
                id_val = actor_prefix[actor_prefix.rfind('_') + 1:].replace('.wem', '').replace('"', '').strip()
                actor_prefix = actor_prefix[:actor_prefix.rfind('_')]
                lines[i + 2] = replaceId(lines[i + 2], id_val, new_ids)
                
                if os.path.exists(f'{redkit_mod_path}\\speech\\en\\audio\\{actor_prefix}_{new_ids[id_val]}.wem'): # already renamed
                    showLogLine(f'speech\\en\\audio\\{actor_prefix}_{id_val}.wem already renamed', 'yellow')
                elif os.path.exists(f'{redkit_mod_path}\\speech\\en\\audio\\{actor_prefix}_{id_val}.wem'):
                    os.rename(f'{redkit_mod_path}\\speech\\en\\audio\\{actor_prefix}_{id_val}.wem',
                              f'{redkit_mod_path}\\speech\\en\\audio\\{actor_prefix}_{new_ids[id_val]}.wem')
                    if os.path.exists(f'{redkit_mod_path}\\speech\\en\\audio_original\\{actor_prefix}_{id_val}.wav'):
                        os.rename(f'{redkit_mod_path}\\speech\\en\\audio_original\\{actor_prefix}_{id_val}.wav',
                                  f'{redkit_mod_path}\\speech\\en\\audio_original\\{actor_prefix}_{new_ids[id_val]}.wav')
                else:
                    showLogLine(f'RENAMING FILE ERROR!!! speech\\en\\audio\\{actor_prefix}_{id_val}.wem DOESN\'T EXIST', 'yellow')

        open(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(filename)}.json', 'w', encoding='utf-8').writelines(lines)
        

# Export json files to cr2w
def exportFiles(files):

    global log_file
    
    totalnum = len(files)
    counter = 1
    
    for filename in files:
        showLogLine(f'[{counter}/{totalnum}] {filename.replace(f'{redkit_mod_path}\\workspace\\', "")}', 'white')
        counter += 1
        
        # Backup
        os.makedirs(filename[:filename.rfind('\\')].replace('workspace', 'RedkitFixer_backups'), exist_ok=True)
        
        shutil.copyfile(filename, filename.replace('workspace', 'RedkitFixer_backups'))  
        
        process = subprocess.Popen([WolvenKit_path, "--json2cr2w",
                                    "--input", f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(filename)}.json',
                                    "--output", filename],
                                   stdout=log_file, stderr=log_file)
        process.wait()  
        
        if process.returncode != 0:
            showLogLine('WOLVENKIT json2cr2w2 CONVERTATION ERROR!!! FILE WAS SKIPPED', 'red')
            failed_files.append(filename)
            
             
          
# Assignment wems and res paths to dialogue lines
def assignWemsAndLipsync(files): # files have to contain only w2scene files paths 
    
    global log_file
    
    modified_files = []
    totalnum = len(files)
    counter = 1
    
    for filename in files.keys():
        lines = open(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(filename)}.json', encoding='utf-8').readlines()
        
        showLogLine(f'[{counter}/{totalnum}] ' + filename.replace(f'{redkit_mod_path}\\workspace\\', ''), 'white')
        counter += 1
        wasModified = False
        
        for i in range(len(lines)):
            if 'voiceFileName' in lines[i]:

                voice_filename = lines[i + 2].replace('_value": ', '').replace('"', '').replace('\n', '').strip()

                if os.path.exists(f"{redkit_mod_path}\\speech\\en\\lipsync\\{voice_filename}.re"):
                    showLogLine(f'    speech\\en\\lipsync\\{voice_filename}.re', 'white')
                    lipsyncPart = ['        },\n',
                                   '        "overriddenLipsyncFilePath": {\n',
                                   '          "_type": "String",\n',
                                  f'          "_value": "speech\\\\en\\\\lipsync\\\\{voice_filename}.re"\n']
                else:
                    lipsyncPart = []

                if os.path.exists(f"{redkit_mod_path}\\speech\\en\\audio\\{voice_filename}.wem"):
                    showLogLine(f'    speech\\en\\audio\\{voice_filename}.wem', 'white')
                    audioPart = ['        },\n',
                                 '        "overriddenAudioFilePath": {\n',
                                 '          "_type": "String",\n',
                                f'          "_value": "speech\\\\en\\\\audio\\\\{voice_filename}.wem"\n']
                else:
                    audioPart = []

                if len(audioPart) + len(lipsyncPart) == 0: # Nothing to do
                    continue

                # case 1: end of chunk
                if lines[i + 3].strip() == '}': 
                    lines = lines[:i + 3] + lipsyncPart + audioPart + lines[i + 3:]
                    wasModified = True

                # case 1: Lipsync is the next element
                elif lines[i + 4].strip() == '"overriddenLipsyncFilePath": {': 

                    if len(lipsyncPart) != 0:
                        lines[i + 6] = lipsyncPart[-1] # update
                        wasModified = True

                    if len(audioPart) != 0:
                    
                        # case 1.1: end of chunk
                        if (lines[i + 7].strip() == '}'): 
                            lines = lines[:i + 7]  + audioPart + lines[i + 7:]
                            wasModified = True
                            
                        # case 1.2: audio element exists 
                        elif (lines[i + 8].strip() == '"overriddenAudioFilePath": {'):
                            lines[i + 10] = audioPart[-1]
                            wasModified = True
                            
                        else: # smth non-standard
                            showLogLine('ASSINGMENT ERROR!!! FILE WASN\'T COMPLETED', 'red')
                            failed_files.append(filename)

                # case 2: Audio is the next element
                elif lines[i + 4].strip() == '"overriddenAudioFilePath": {': 

                    if len(audioPart) != 0:
                        lines[i + 6] = audioPart[-1] # update
                        wasModified = True

                    if len(lipsyncPart) != 0:
                    
                        # case 2.1: lipsync element exists (not sure this could be)
                        if (lines[i + 8].strip() == '"overriddenLipsyncFilePath": {'):
                            lines[i + 10] = lipsyncPart[-1]
                            wasModified = True
                            
                        # case 2.2: end of chunk
                        elif (lines[i + 7].strip() == '}'): 
                            lines = lines[:i + 3]  + lipsyncPart + lines[i + 3:]
                            wasModified = True
                            
                        else: # smth non-standard
                            showLogLine('ASSINGMENT ERROR!!! FILE WASN\'T COMPLETED', 'red')
                            failed_files.append(filename)
                            
                else: # smth non-standard
                    showLogLine('ASSINGMENT ERROR!!! FILE WASN\'T COMPLETED', 'red')
                    failed_files.append(filename)
                    
        if wasModified:
            modified_files.append(filename)
            
        open(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp\\{hash(filename)}.json', 'w', encoding='utf-8').writelines(lines)
        
    return modified_files
    

# Export updated dump to file
def exportStringsDump(dump):
    # Create backup copy
    os.makedirs(f'{redkit_mod_path}\\RedkitFixer_backups\\_StringDataBase_export', exist_ok=True)

    timestamp = str(int(time.time()))
    shutil.copyfile(f'{redkit_mod_path}\\LocalEditorStringDataBaseW3_UTF8_mod_export.csv',
                    f'{redkit_mod_path}\\RedkitFixer_backups\\_StringDataBase_export\\db_backup_{timestamp}.csv')  

    with open(f'{redkit_mod_path}\\LocalEditorStringDataBaseW3_UTF8_mod_export.csv', 'w', encoding='utf-8') as f:
        f.write('ID;RESOURCE;PROPERTY;VOICEOVER;KEY;BR;CZ;RU;AR;TR;CN;PL;IT;FR;DE;ZH;ESMX;EN;KR;ES;JP;HU\n')
        for d in dump:
            if d[-1] == True:
                f.write(';'.join(d[:-1]) + '\n')


def printHelp():
    print('\nUse:')
    print('    ' + cmd_color('green', '--assign-audio-and-lipsync') + ' to add .wem and .re paths to scenes files')
    print('    ' + cmd_color('green', '--clean-unused') + ' to clean unused strings')
    print('    ' + cmd_color('green', '--change-id-space ') + cmd_color('yellow', 'your_mod_nexus_id') + ' to clean unused strings and change id-spaces')
    print('\nYou can get ' + cmd_color('yellow', 'your_mod_nexus_id') +' from your mod URL.')
    print('E.g. for https://www.nexusmods.com/witcher3/mods/' + cmd_color('green','9453') + cmd_color('yellow', ' your_mod_nexus_id') + ' is ' + cmd_color('green', '9453'))


def countFiles(path, ext=[]):
    files_num = 0
    
    for _, _, files in os.walk(path):
        if len(ext) == 0:
            files_num += len(files)
        else:
            files_num += sum([1 for filename in files if filename[filename.rfind('.'):] in ext])
        
    return files_num


def showLogLine(line, color='green'):
    print(cmd_color(color, line))
    log_file.write(line + '\n')


if __name__ == "__main__":

    colorama.just_fix_windows_console()
    
    # Checking paths
    if os.path.exists(WolvenKit_path) & os.path.exists(redkit_mod_path) & (len(sys.argv) > 1):
    
        # Help
        if (sys.argv[1] == '--help') | (sys.argv[1] == '-help') | (sys.argv[1] == 'help'):
            printHelp()
            sys.exit()
            
        # Checking option
        if (sys.argv[1] != '--change-id-space') & (sys.argv[1] != '--clean-unused') & (sys.argv[1] != '--assign-audio-and-lipsync'):

            print(cmd_color('red', f'Option not set.'))
            printHelp()
            sys.exit()

        # Checking id-space
        if (sys.argv[1] == '--change-id-space'):
            if len(sys.argv) != 3:
                print(cmd_color('red', 'Error: your_mod_nexus_id not set'))
                print('\nYou can get ' + cmd_color('yellow', 'your_mod_nexus_id') +' from your mod URL.')
                print('E.g. for https://www.nexusmods.com/witcher3/mods/' + cmd_color('green','9453') + cmd_color('yellow', ' your_mod_nexus_id') + ' is ' + cmd_color('green', '9453'))
                sys.exit()
            elif (not sys.argv[2].isnumeric()) | (len(sys.argv[2]) > 5) | (len(sys.argv[2]) < 4):
                print(cmd_color('red', 'Error: incorrest your_mod_nexus_id.') + ' You can get it from your mod URL. E.g. for https://www.nexusmods.com/witcher3/mods/9453 your_mod_nexus_id is 9453.')
                sys.exit()

        os.makedirs(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp', exist_ok=True)
        os.makedirs(f'{redkit_mod_path}\\logs', exist_ok=True)
            
        with open(f'{redkit_mod_path}\\logs\\project_fixer_log{sys.argv[1]}.txt', 'w', encoding='utf-8') as log_file:
            
            if sys.argv[1] == '--assign-audio-and-lipsync': 
                
                if (not os.path.exists(f'{redkit_mod_path}\\speech\\en\\lipsync')):
                    print(cmd_color('red', 'You have no lipsync files!'))
                    sys.exit()
                
                showLogLine('\nDetecting strings in files...')
                files_strings = getStrIdsFromFiles(f'{redkit_mod_path}\\workspace', True)

                showLogLine('\nProcessing files...')
                modified_files = assignWemsAndLipsync(files_strings)
                
                showLogLine(f'\n{len(modified_files)} files were modified.')
                
                showLogLine('\nExport files...')
                
                exportFiles(modified_files)
                
                showLogLine('\nDone!')
                
                print(cmd_color('green', '\nBackup files are here:') + f' {redkit_mod_path}\\RedkitFixer_backups\\') 
                
                if len(failed_files) > 0: 
                    print(cmd_color('yellow', '\nSome errors occured in files unconverted. .re and .wem files for skipped files weren\'t assigned.'))                     
                    print(cmd_color('yellow', 'Skipped files are:\n' + '\n'.join(list(set(failed_files)))))
                    log_file.write('\nSome errors occured in files unconverted. .re and .wem files for skipped files weren\'t assigned.\nSkipped files are:\n' + '\n'.join(list(set(failed_files))))
                else:
                    print(cmd_color('green', '\n0 files were skipped.'))
              
            else:
                showLogLine('\nDetecting strings in files...')
                files_strings = getStrIdsFromFiles(f'{redkit_mod_path}\\workspace')

                showLogLine('\nReading REDkit strings dump...')
                redkit_strings = getStringsFromDump(f'{redkit_mod_path}\\LocalEditorStringDataBaseW3_UTF8_mod_export.csv')

                showLogLine('\nCleaning unused strings...')
                redkit_strings = validateStrings(redkit_strings, files_strings)

                if sys.argv[1] == '--clean-unused':

                    # export                                                                                          
                    exportStringsDump(redkit_strings)

                    showLogLine('\nCleaning is finished!')
                    
                    print(cmd_color('green', '\nBefore cleaning: ') + str(len(redkit_strings)) + ' strings. ' +\
                          cmd_color('green', '\nAfter cleaning: ') + str(len([data for data in redkit_strings if data[-1] == True])) + ' strings. ')
                    print(cmd_color('green', '\nCleared strings dump is here:'))
                    print(f'{redkit_mod_path}\\LocalEditorStringDataBaseW3_UTF8_mod_export.csv\n') 

                else: # sys.argv[1] == '--change-id-space'

                    new_idspace = 1000000000 + int(sys.argv[2]) * 10000 

                    showLogLine('Generating new ids...\n')
                    redkit_strings = reassignIdsDump(redkit_strings, new_idspace) 

                    showLogLine('\nChanging ids in files...')
                    changeIdsInFiles(redkit_strings, files_strings)

                    showLogLine('\nExport files...')
                    exportFiles(files_strings.keys())
                    
                    local_failed_resources = [filepath.replace(f'{redkit_mod_path}\\workspace\\', '') for filepath in failed_files]
                    for line in redkit_strings:
                        if not getPath(line[1]) in local_failed_resources:
                            line[0] = line[-1] # New id to id
                        line[-1] = True
                    
                    # export                                                                                    
                    exportStringsDump(redkit_strings)
                    
                    print(cmd_color('green', '\nId changing finished!'))
                    print(cmd_color('green', '\nBackup files are here:') + f' {redkit_mod_path}\\RedkitFixer_backups\\')  
                                        
                    print(cmd_color('red', '\nDon\'t forget to update id-space in REDkit and replace strings in LocalEditorStringDataBaseW3_UTF8_mod using new export file!'))  
                    print(cmd_color('green', 'Your new id-space: ') + f' {new_idspace}\n')   
                    print(cmd_color('green', 'Updated strings dump is here: ') + f'{redkit_mod_path}\\LocalEditorStringDataBaseW3_UTF8_mod_export.csv')  
                    
                print(cmd_color('green', '\nStrings dump backup (previous LocalEditorStringDataBaseW3_UTF8_mod_export.csv) is here:'))
                print(f'{redkit_mod_path}\\RedkitFixer_backups\\_StringDataBase_export\\db_backup_{timestamp}.csv')
                    
                if len(failed_files) > 0:
                    print(cmd_color('yellow', '\nSome errors occured in files conversion. Check if skipped files have strings with an old id-space.'))    
                    print(cmd_color('yellow', 'Skipped files are:\n') + '\n'.join(list(set(failed_files))))  
                    log_file.write('\nSome errors occured in files conversion. Check if skipped files have strings with an old id-space.\nSkipped files are:\n' + '\n'.join(list(set(failed_files)))) 
                else:
                    print(cmd_color('green', '\n0 files were skipped.'))
            
        shutil.rmtree(f'{redkit_mod_path}\\RedkitFixer_backups\\_tmp')
                           
    else:
        if not os.path.exists(WolvenKit_path):
            print(cmd_color('red', f'{WolvenKit_path} is not found. Check WolvenKit.CLI.exe path'))

        if not os.path.exists(redkit_mod_path):
            print(cmd_color('red', f'{redkit_mod_path} is not found. Check Redkit project path'))

        if len(sys.argv) < 2:
            print(cmd_color('red', f'ERROR: option not set.'))
            printHelp()