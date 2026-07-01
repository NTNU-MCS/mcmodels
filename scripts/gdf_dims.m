function [Lpp, Boa, T] = gdf_dims(gdfFile)
fid = fopen(gdfFile); fgetl(fid);            % header
fscanf(fid,'%f %f',2);                       % ULEN, GRAV
sym = fscanf(fid,'%d %d',2);                 % ISX, ISY
N   = fscanf(fid,'%d',1);                    % no. of panels
V   = fscanf(fid,'%f %f %f',[3 4*N])';       % vertices
fclose(fid);
Lpp = max(V(:,1)) - min(V(:,1));
Boa = max(V(:,2)) - min(V(:,2));
if sym(1), Lpp = 2*max(abs(V(:,1))); end
if sym(2), Boa = 2*max(abs(V(:,2))); end
T   = -min(V(:,3));
end