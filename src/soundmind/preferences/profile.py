from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from soundmind.preferences.models import ListeningEvent, ListeningEventType, TasteProfile


@dataclass(frozen=True)
class PreferenceSignal:
    track_id:str
    positive:float=0.0
    negative:float=0.0
    replay:float=0.0
    skip:float=0.0
    @property
    def net_preference(self)->float:
        return self.positive+self.replay-self.negative-self.skip

class TasteProfileBuilder:
    def __init__(self,*,half_life_days:float=30.0):
        if half_life_days<=0: raise ValueError("half_life_days must be positive")
        self.half_life_days=half_life_days
    def signal(self,event:ListeningEvent,*,now:datetime)->PreferenceSignal:
        age_days=max(0.0,(now-event.occurred_at).total_seconds()/86400.0)
        decay=0.5**(age_days/self.half_life_days)
        weights={
            ListeningEventType.PLAY:(.15,0,0,0),
            ListeningEventType.COMPLETE:(.35,0,0,0),
            ListeningEventType.LIKE:(1,0,0,0),
            ListeningEventType.DISLIKE:(0,1,0,0),
            ListeningEventType.REPLAY:(0,0,1.25,0),
            ListeningEventType.SKIP:(0,0,0,.75),
        }
        p,n,r,s=weights[event.event_type]
        return PreferenceSignal(event.track_id,p*decay,n*decay,r*decay,s*decay)
    def build(self,events:list[ListeningEvent],*,now:datetime)->TasteProfile:
        positive=Counter(); negative=Counter(); replay=Counter(); skipped=Counter()
        for event in events:
            signal=self.signal(event,now=now)
            if signal.positive>0: positive[event.track_id]+=signal.positive
            if signal.negative>0: negative[event.track_id]+=signal.negative
            if signal.replay>0: replay[event.track_id]+=signal.replay
            if signal.skip>0: skipped[event.track_id]+=signal.skip
        return TasteProfile(
            tuple(k for k,_ in positive.most_common()),
            tuple(k for k,_ in negative.most_common()),
            tuple(k for k,_ in replay.most_common()),
            tuple(k for k,_ in skipped.most_common()),
            tuple(sorted({e.context for e in events if e.context})),
        )
