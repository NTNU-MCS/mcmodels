% walk the directories that follows the pattern hydro/wamit/outputs
% bring in the file name without the extension, such as `*/hydro/wamit/outputs/<filename>.*`
% for each file, check if there is a corresponding .cfg file in the same directory
% print the name. the files must be in a directory called 'outputs'.

% matlab 2025a

% get the directory with respect to the scripts location
script_dir = fileparts(mfilename('fullpath'));
data_dir = fullfile(script_dir, '..', 'data', 'vessels');

% walk through the directories
files = dir(fullfile(data_dir, '**', 'outputs', '*.*'));

list_of_files = {};

for i = 1:length(files)
    file = files(i);
    [file_path, name, ~] = fileparts(file.name);

    % check for corresponding .cfg file
    cfg_file = fullfile(file.folder, [name, '.cfg']);
    if exist(cfg_file, 'file')
        % add to list of files path + name without extension while preventing duplicates
        name_to_record = fullfile(file.folder, name);
        if ~ismember(name_to_record, list_of_files)
            list_of_files{end+1} = name_to_record; %#ok<SAGROW>
        end
    else
        continue
    end
end

