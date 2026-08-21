function vessel = fix_frc_mass_matrix(vessel, frcfile)
% FIX_FRC_MASS_MATRIX Correct vessel.main.CG/vessel.MRB when wamit2vessel.m
% misreads a RHO/VCG/IMASS-style .frc file as its "Alternative 1" format.
%
%   vessel = fix_frc_mass_matrix(vessel, frcfile)
%
% wamit2vessel.m (MSS toolbox, HYDRO/wamit2vessel.m) decides between two
% .frc parsing conventions with:
%
%   frc = dlmread(frcfile,'',1,0);
%   if frc(5,1) < 1000        % "Alternative 1"
%       VCG = frc(2,1);
%       vessel.main.CG = [0 0 T_draught+VCG];
%       ...                    % k44/k55/k66/k46 read from more wrong rows
%   else                       % "Alternative 2"
%       xg = frc(3,1); yg = frc(3,2); zg = frc(3,3);
%       MRB = frc(5:10,1:6);
%
% This heuristic assumes an "Alternative 2" (direct 6x6 mass matrix) .frc
% file will have a surge mass >= 1000 at row 5, column 1. That is false
% for every model-scale vessel in this repo with mass < 1000 kg (all of
% drillship/enterprise/voyager, at time of writing) even though their
% .frc files are genuinely laid out as:
%
%   line 2: IOPTN(1-9)
%   line 3: RHO
%   line 4: VCG = [xg yg zg]
%   line 5: IMASS (1 = direct 6x6 mass matrix follows)
%   line 6-11: MRB (if IMASS == 1)
%
% which is exactly what "Alternative 2" parsing expects. For these
% vessels wamit2vessel.m instead takes the "Alternative 1" branch,
% misreads RHO (line 3) as a scalar VCG, and produces
% vessel.main.CG = [0 0 T_draught+1000] plus a near-zero rotational MRB
% (roll/pitch/yaw inertia lost, since k44/k55/k66/k46 also get read from
% the wrong file positions under the same misdetection).
%
% This function independently re-parses the .frc file using the known
% RHO/VCG/IMASS layout (not wamit2vessel.m's row(5,1)<1000 heuristic) and
% overwrites vessel.main.CG/vessel.MRB when they disagree with what
% wamit2vessel.m produced. It is a no-op (beyond a sanity check) for .frc
% files where wamit2vessel.m's heuristic happens to pick the right branch
% already (e.g. any vessel with mass >= 1000 kg, such as milliAmpere1).
%
% Only the IMASS == 1 (direct mass matrix) form is handled -- that is the
% form every .frc file in this repo currently uses. IMASS == 0 (radii of
% gyration form) is not implemented and raises an error rather than
% silently producing something unverified.
%
% Inputs:
%   vessel   MSS vessel structure, as returned by wamit2vessel
%   frcfile  path to the *.frc file wamit2vessel was pointed at
%
% Outputs:
%   vessel   same structure, with main.CG/MRB corrected if needed

    frc = dlmread(frcfile, '', 1, 0);  %#ok<DLMRD> -- mirrors wamit2vessel.m's own parsing

    xg     = frc(3, 1);
    yg     = frc(3, 2);
    zg     = frc(3, 3);
    imass  = frc(4, 1);

    if imass ~= 1
        error(['fix_frc_mass_matrix: only IMASS == 1 (direct 6x6 mass ' ...
               'matrix) .frc files are supported, got IMASS == %g in %s. ' ...
               'This vessel needs the radii-of-gyration form implemented ' ...
               'and verified before this check can be trusted.'], imass, frcfile);
    end

    MRB_correct = frc(5:10, 1:6);
    CG_correct  = [xg yg zg];

    if ~isfield(vessel, 'main') || ~isfield(vessel.main, 'CG') || ~isfield(vessel, 'MRB')
        warning('fix_frc_mass_matrix:missing_fields', ...
            ['vessel.main.CG/vessel.MRB were never set by wamit2vessel -- ' ...
             'likely an earlier failure in wamit2vessel (e.g. a missing ' ...
             '.pot/.1/.3/.4/.8/.out file in processed/) rather than the FRC ' ...
             'alt-detection bug this function normally works around. Setting ' ...
             'them from %s anyway, but check the wamit2vessel output above ' ...
             'for the real error first.'], frcfile);
        vessel.main.CG = CG_correct;
        vessel.MRB = MRB_correct;
        return
    end

    if isequal(vessel.main.CG, CG_correct) && isequal(vessel.MRB, MRB_correct)
        return  % wamit2vessel.m already got this one right
    end

    warning('fix_frc_mass_matrix:corrected', ...
        ['wamit2vessel.m misread %s (frc(5,1) < 1000 heuristic picked the ' ...
         'wrong FRC alternative for this mass-%g-kg vessel). Correcting ' ...
         'vessel.main.CG from %s to %s and restoring vessel.MRB from the ' ...
         'raw .frc mass matrix.'], ...
        frcfile, MRB_correct(1, 1), mat2str(vessel.main.CG), mat2str(CG_correct));

    vessel.main.CG = CG_correct;
    vessel.MRB = MRB_correct;
end
