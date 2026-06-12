clear all;
% addpath(manage_paths());
addpath(genpath(pwd));

filename = '../data/vessels/voyager/hydro/wamit/outputs/voyager';
[Lpp, Boa, T_draught] = gdf_dims('../data/vessels/voyager/hydro/wamit/mesh/voyager.gdf');

plot_flag = '0000';
vessel = wamit2vessel(filename,T_draught,Lpp,Boa,plot_flag);

vessel_wamit_json_string = jsonencode(vessel, 'PrettyPrint', true);

vessel_wamit_json_file_name = '../data/vessels/voyager/hydro/wamit/outputs/vessel_wamit.json';
fid = fopen(vessel_wamit_json_file_name , 'w');
if fid == -1
    error('Cannot open file for writing.');
end
fprintf(fid, '%s', vessel_wamit_json_string);
fclose(fid);

vessel_abc = vessel2ss(vessel);

vessel_wamit_abc_json_string = jsonencode(vessel_abc, 'PrettyPrint', true);

vessel_wamit_abc_json_filename = '../data/vessels/voyager/hydro/wamit/outputs/vessel_wamit_abc.json';
fid = fopen(vessel_wamit_abc_json_filename , 'w');
if fid == -1
    error('Cannot open file for writing.');
end
fprintf(fid, '%s', vessel_wamit_abc_json_string);
fclose(fid);
