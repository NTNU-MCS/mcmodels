clear all;


% --- Configuration ---
vessel_name = strtrim(input('Enter vessel name: ', 's'));
% ---------------------

% Get the directory where this script is located
[script_dir, ~, ~] = fileparts(mfilename('fullpath'));
scriptFolder = fileparts(mfilename('fullpath'));
base_dir = fullfile(script_dir, '..');
addpath(genpath(base_dir));

% Define base data directories dynamically
vessel_base_dir = fullfile(script_dir, '..', 'data', 'vessels', vessel_name, 'hydro', 'wamit');
processed_dir     = fullfile(vessel_base_dir, 'processed');
mesh_dir        = fullfile(vessel_base_dir, 'mesh');

% Define file paths using the vessel name variable
filename = fullfile(processed_dir, vessel_name);
gdf_file = fullfile(mesh_dir, [vessel_name, '.gdf']);

% Load dimensions: read from the mesh GDF file if it exists, otherwise
% ask the user for them directly.
if exist(gdf_file, 'file') == 2
    [Lpp, Boa, T_draught] = gdf_dims(gdf_file);
else
    warning('GDF file not found: %s. Enter vessel dimensions manually.', gdf_file);
    Lpp       = input('Lpp (length between perpendiculars) [m]: ');
    Boa       = input('Boa (breadth overall) [m]: ');
    T_draught = input('T_draught (draught) [m]: ');
end
fprintf("Lpp: %f, Boa: %f, T_draught: %f\n", Lpp, Boa, T_draught);
fprintf("Filename: %s", filename);
plot_flag = '0000';
vessel = wamit2vessel(filename, T_draught, Lpp, Boa, plot_flag);

vessel.main.name = vessel_name;

% --- Write vessel.wamit.json ---
vessel_wamit_json_string = jsonencode(vessel, 'PrettyPrint', true);
vessel_wamit_json_file_name = fullfile(processed_dir, 'vessel.wamit.json');

fid = fopen(vessel_wamit_json_file_name, 'w');
if fid == -1
    error('Cannot open file for writing: %s', vessel_wamit_json_file_name);
end
fprintf(fid, '%s', vessel_wamit_json_string);
fclose(fid);

% --- Process State Space and write vessel.wamit.abc.json ---
% vessel2ss requires no real frequency above its infinite-frequency
% stand-in (10 rad/s); Voyager's model-scale period sweep produces some
% real frequencies above that, so restrict just the copy fed to vessel2ss
% (vessel.wamit.json above keeps the full, untouched frequency range).
vessel_for_ss = restrict_vessel_for_state_space(vessel);
vessel_abc = vessel2ss(vessel_for_ss);

vessel_wamit_abc_json_string = jsonencode(vessel_abc, 'PrettyPrint', true);
vessel_wamit_abc_json_filename = fullfile(processed_dir, 'vessel.wamit.abc.json');

fid = fopen(vessel_wamit_abc_json_filename, 'w');
if fid == -1
    error('Cannot open file for writing: %s', vessel_wamit_abc_json_filename);
end
fprintf(fid, '%s', vessel_wamit_abc_json_string);
fclose(fid);