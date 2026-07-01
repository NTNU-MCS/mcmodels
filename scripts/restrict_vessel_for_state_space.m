function vessel_ss = restrict_vessel_for_state_space(vessel, w_inf)
% RESTRICT_VESSEL_FOR_STATE_SPACE Trim vessel.freqs/A/B/C so vessel2ss (MSS
% toolbox) can process them.
%
%   vessel_ss = restrict_vessel_for_state_space(vessel)
%   vessel_ss = restrict_vessel_for_state_space(vessel, w_inf)
%
% vessel2ss.m hardcodes w_inf (default 10 rad/s) as its stand-in for
% infinite frequency and requires it to be the largest value in
% vessel.freqs. Model-scale vessels (short periods) can have real
% WAMIT-computed frequencies above that. This function drops those
% points for the state-space fit only -- pass the original, untouched
% vessel struct to jsonencode/wherever the full frequency-domain data is
% still needed.
%
% Inputs:
%   vessel   MSS vessel structure (from wamit2vessel)
%   w_inf    infinite-frequency stand-in used by vessel2ss (default: 10)
%
% Outputs:
%   vessel_ss   copy of vessel with freqs/A/B/C restricted to
%               [0, real frequencies < w_inf, w_inf]

    if nargin < 2
        w_inf = 10;
    end

    freqs = vessel.freqs;
    idx_zero = find(freqs == 0);
    idx_inf  = find(freqs == w_inf);
    idx_keep = find(freqs > 0 & freqs < w_inf);

    if isempty(idx_zero) || isempty(idx_inf)
        error(['vessel.freqs must contain both 0 and %g ' ...
               '(zero-/infinite-frequency stand-ins)'], w_inf);
    end

    [~, order] = sort(freqs(idx_keep));
    idx_keep = idx_keep(order);

    idx = [idx_zero, idx_keep, idx_inf];

    n_dropped = length(freqs) - length(idx);
    if n_dropped > 0
        warning('restrict_vessel_for_state_space:dropped', ...
            ['%d frequency point(s) above %g rad/s dropped for the ' ...
             'state-space fit (vessel2ss requires %g to be the highest ' ...
             'frequency).'], n_dropped, w_inf, w_inf);
    end

    vessel_ss = vessel;
    vessel_ss.freqs = freqs(idx);
    vessel_ss.A = vessel.A(:,:,idx);
    vessel_ss.B = vessel.B(:,:,idx);
    vessel_ss.C = vessel.C(:,:,idx);
end
