clear all;

graphics_toolkit("qt");

% Load necessary Octave packages (if installed)
% 'struct' is often needed for advanced JSON handling, but native 'tojson' works too.
pkg load struct;

% --- Configuration ---
vessel_name = 'voyager'; % Change this to change the target vessel
% ---------------------

% Get the directory where this script is located
% Note: In Octave, mfilename('fullpath') works perfectly when run as a script.
[script_dir, ~, ~] = fileparts(mfilename('fullpath'));

% Add the script's directory and its subfolders to the Octave path
addpath(genpath(script_dir));

% Define base data directories dynamically
vessel_base_dir = fullfile(script_dir, 'data', 'vessels', vessel_name, 'hydro', 'wamit');
outputs_dir     = fullfile(vessel_base_dir, 'outputs');
mesh_dir        = fullfile(vessel_base_dir, 'mesh');

% Define file paths using the vessel name variable
filename = fullfile(outputs_dir, vessel_name);
gdf_file = fullfile(mesh_dir, [vessel_name, '.gdf']);

% Load dimensions and run wamit2vessel
[Lpp, Boa, T_draught] = gdf_dims(gdf_file);
fprintf("Lpp: %f, Boa: %f, T_draught: %f\n", Lpp, Boa, T_draught);

plot_flag = '0000';
vessel = wamit2vessel(filename, T_draught, Lpp, Boa, plot_flag);

% --- Write vessel.wamit.json ---
% Octave uses 'tojson' natively. It doesn't have a 'PrettyPrint' flag,
% but it generates valid minified JSON.
vessel_wamit_json_string = tojson(vessel);
vessel_wamit_json_file_name = fullfile(outputs_dir, 'vessel.wamit.json');

fid = fopen(vessel_wamit_json_file_name, 'w');
if fid == -1
    error('Cannot open file for writing: %s', vessel_wamit_json_file_name);
end
fprintf(fid, '%s', vessel_wamit_json_string);
fclose(fid);

% --- Process State Space and write vessel.wamit.abc.json ---
vessel_abc = vessel2ss(vessel);

vessel_wamit_abc_json_string = tojson(vessel_abc);
vessel_wamit_abc_json_filename = fullfile(outputs_dir, 'vessel.wamit.abc.json');

fid = fopen(vessel_wamit_abc_json_filename, 'w');
if fid == -1
    error('Cannot open file for writing: %s', vessel_wamit_abc_json_filename);
end
fprintf(fid, '%s', vessel_wamit_abc_json_string);
fclose(fid);