from soundmind.preferences.profile import PreferenceSignal


def preference_score(signal:PreferenceSignal)->float:
    return signal.net_preference

def preference_boost(signal:PreferenceSignal,*,minimum:float=-1.0,maximum:float=1.0)->float:
    if minimum>=maximum: raise ValueError("minimum must be less than maximum")
    return max(minimum,min(maximum,preference_score(signal)))
