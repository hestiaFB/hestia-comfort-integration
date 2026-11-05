"""Optional, explicitly estimated features for solar protection, airing and air.

No commands, inferred equipment state, or guaranteed air renewal are produced.
"""
from datetime import datetime, timedelta
import math

from . import voc as vocs

# The integrations that drive a cover with the sun, by the key cover_link.py gives them.
DRIVERS = {'adaptive_cover_pro': 'Adaptive Cover Pro', 'cover_automatic': 'CoverAutomatic', 'cover_extender': 'Cover Extender'}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _value(readings, key):
    r = readings.get(key)
    return r.value if r and r.usable else None


def _ventilation(readings):
    """A ventilation unit, possibly with a high-speed position: running if either position runs."""
    keys = [k for k in ('ventilation', 'ventilation_boost') if k in readings]
    if not keys:
        return None
    values = [_value(readings, k) for k in keys]
    on = True if any(v is True for v in values) else False if all(v is False for v in values) else None
    return {'on': on, 'boost': _value(readings, 'ventilation_boost') is True}


def air_features(readings, settings, context):
    def status(key, threshold):
        if key not in readings:
            return 'not_configured'
        value = _value(readings, key)
        return 'unknown' if value is None else 'high' if value >= threshold else 'ok'
    pm = status('pm25', settings.pm25_action)
    purifier_on = _value(readings, 'purifier') is True
    # A running purifier is the remedy for particles: they no longer call for opening.
    pm_treated = pm == 'high' and purifier_on
    voc, threshold = readings.get('voc'), context.get('voc_threshold')
    vs = 'not_configured' if voc is None else 'unknown' if not voc.usable else 'uninterpreted'
    judged = {}
    if (voc and voc.usable and isinstance(threshold, dict) and _number(threshold.get('value'))
            and threshold['value'] > 0 and isinstance(threshold.get('unit'),str) and threshold['unit'] == (voc.unit or '')):
        # Judged on its recent mean, with a margin, a delay and a pause after an airing (engine/voc.py).
        def setting(key, default):
            value = context.get(key)
            return value if _number(value) else default
        judged = vocs.judge(voc.value, threshold['value'], context.get('now'), mean=context.get('voc_mean'),
                            was_high=context.get('voc_was_high') is True, above_since=context.get('voc_above_since'),
                            delay=setting('voc_delay_minutes', vocs.DELAY_MINUTES),
                            pause=setting('voc_pause_minutes', vocs.PAUSE_MINUTES),
                            aired_at=context.get('voc_aired_at'), aired_after=context.get('voc_aired_after'),
                            falling=context.get('voc_falling') is True, outdoor=context.get('voc_outdoor') is True,
                            opened_at_level=context.get('voc_opened_level'), going=context.get('voc_going') is True,
                            shut=context.get('voc_shut') if isinstance(context.get('voc_shut'), bool) else None)
        vs = 'high' if judged['high'] else 'ok'
    covered = [label for key, label in (('co2','CO₂'),('pm25','PM2.5'),('voc','COV')) if _value(readings,key) is not None]
    missing = [label for key, label in (('co2','CO₂'),('pm25','PM2.5'),('voc','COV')) if _value(readings,key) is None]
    coverage = 'Mesures disponibles : ' + (', '.join(covered) or 'aucune')
    if missing:
        coverage += ' ; non suivies ou indisponibles : ' + ', '.join(missing)
    messages = []
    if pm == 'high': messages.append('PM2.5 élevées : le purificateur les filtre.' if pm_treated else 'PM2.5 élevées : besoin d’air maintenu sous réserve des conditions extérieures.')
    if vs == 'high':
        # An index without unit (Sensirion) is relative to the home's own mean: « l'habituel ».
        above = 'COV au-dessus du seuil' if voc.unit else 'COV au-dessus de l’habituel'
        messages.append(f"{above} depuis {judged['minutes']} min : besoin d’air maintenu." if judged.get('minutes')
                        else f"{above} : besoin d’air maintenu.")
    if vs == 'uninterpreted': messages.append('COV mesurés, interprétation indisponible sans seuil de même unité.')
    if 'purifier' in readings:
        messages.append('Le purificateur ne renouvelle pas l’air et ne retire pas le CO₂ ; son action sur les COV n’est pas présumée.')
    return dict(pm25_status=pm,voc_status=vs,voc_unit=voc.unit if voc else None,
                voc_above_since=judged.get('above_since'),voc_minutes=judged.get('minutes'),voc_mean=judged.get('mean'),
                voc_paused=judged.get('paused', False),
                # What holds a high index back: falling by itself, opening makes it climb at this hour, or it climbs
                # with the window open now (engine/voc.py).
                voc_falling=judged.get('falling', False),voc_outdoor=judged.get('outdoor', False),
                voc_rising_open=judged.get('rising', False),
                purifier={'on':_value(readings,'purifier'),'speed':_value(readings,'purifier_speed')},pm25_treated=pm_treated,
                ventilation=_ventilation(readings),
                coverage=coverage,message=' '.join(messages) or 'Les mesures d’air restent distinctes.')


def _presence(readings, context):
    sources = {k.split(':',1)[1]:r for k,r in readings.items() if k.startswith('presence:')}
    if not sources:
        return {'state':'not_configured','message':'Présence non suivie.'}
    state = 'unknown'
    if any(r.usable and r.value is True for r in sources.values()):
        state = 'occupied'
    else:
        delay = context.get('presence_delay_minutes',5)
        delay = delay if _number(delay) and 0 <= delay <= 120 else 5
        times = context.get('presence_off_minutes') or {}
        quiet = all(r.usable and r.value is False and r.detail in ('occupancy','presence') and _number(times.get(e)) for e,r in sources.items())
        if quiet and all(times[e] >= delay for e in sources):
            state = 'empty'
        elif quiet:
            # Nobody seen for a few minutes, not yet the delay: said as it is, not « unknown ».
            return {'state':'leaving','minutes':round(min(times[e] for e in sources)),'delay':delay,
                    'message':'Personne détecté depuis quelques minutes ; la pièce sera dite vide après le délai choisi.'}
    return {'state':state,'message':{'occupied':'Présence détectée.', 'empty':'Pièce confirmée vide : suivi du confort et de l’air conservé ; vérifiez les fenêtres ouvertes.',
                                   'unknown':'Présence inconnue ; le silence d’un détecteur de mouvement ne prouve pas l’absence.'}[state]}


def _shade(meta, sun):
    from .assessment import EXPOSURES
    bearing = meta.azimuth if meta.azimuth is not None else EXPOSURES.get(meta.exposure)
    if sun is None or bearing is None:
        return None, 'unknown'
    gap = math.radians(((sun.azimuth-bearing+540)%360)-180)
    facing = math.cos(gap)
    if sun.elevation <= 0 or facing <= 0:
        return 1.0, 'simple'
    if (all(_number(v) for v in (meta.height,meta.overhang_depth,meta.overhang_gap))
            and meta.height > 0 and meta.overhang_depth >= 0 and meta.overhang_gap >= 0):
        shadow = meta.overhang_depth * math.tan(math.radians(min(sun.elevation,89.9))) / facing
        return round(max(0,min(1,(shadow-meta.overhang_gap)/meta.height)),2), 'geometry'
    return (round(1-1/3,2) if meta.sheltered else 0.0), 'simple'


def _soon(start, now, within=120):
    """« 13 h 50 » when the sun reaches the window within two hours, else None (local time of the reading)."""
    from datetime import datetime
    try:
        moment = datetime.fromisoformat(start) if isinstance(start, str) else None
    except ValueError:
        return None
    if moment is None or now is None or moment.tzinfo is None or now.tzinfo is None:
        return None
    minutes = (moment - now).total_seconds() / 60
    return moment.strftime('%H h %M') if 0 < minutes <= within else None


def _shutters(readings, settings, openings, sun, details, needs, now=None):
    by_id={d['entity_id']:d for d in details}
    result=[]
    for eid,meta in openings.items():
        if meta.shutter not in ('manual','connected'):
            continue
        shade,model = _shade(meta,sun)
        d=by_id.get(eid,{})
        watts=d.get('sun_wm2')
        # Details already apply the historical simple shelter attenuation. Geometry
        # replaces it here rather than attenuating the same facade twice.
        if model == 'geometry':
            from .assessment import facade_share, facade_irradiance
            watts=facade_irradiance(facade_share(meta.exposure,sun,meta.azimuth),sun,_value(readings,'solar'))
            if watts is not None: watts *= 1-shade
        position = _value(readings,'cover:'+eid) if meta.shutter == 'connected' else None
        state = _value(readings,'cover_state:'+eid) if meta.shutter == 'connected' else None
        override=_value(readings,'shutter_override:'+meta.override_entity) if meta.override_entity else None
        automatic=_value(readings,'shutter_auto:'+meta.auto_entity) if meta.auto_entity else None
        # The driver knows whether the sun really stands in front of this window (its field of view, its facade).
        driven=bool(meta.driver)
        name=DRIVERS.get(meta.driver,meta.driver)
        front=_value(readings,'shutter_sun:'+eid) if driven else None
        target=_value(readings,'shutter_target:'+eid) if driven else None
        switch=lambda name:_value(readings,f'shutter_{name}:'+eid) if driven else None
        enabled,tracking,detection,climate=switch('enabled'),switch('tracking'),switch('detection'),switch('climate')
        # Without its detection, a hand on the cover goes unseen: the override signal says nothing.
        if detection is False: override=None
        off=('disabled' if enabled is False else 'auto' if automatic is False else 'tracking' if tracking is False else None) if driven else None
        driving=driven and automatic is True and off is None
        strong=watts is not None and watts >= settings.sun_facade
        if front is False: strong=False
        elif front is True and watts is None: strong=True
        advice=None
        message='Position non mesurée.' if position is None else f'Position mesurée : {position:g} %.'
        manual=meta.shutter == 'manual'
        tip=''
        if override is True:
            message += ' Dérogation active respectée.'
        elif strong and 'cool' in needs and position != 0 and state != 'closed':
            advice='close'
            tip=' Si le volet est ouvert, fermez-le pour limiter les apports solaires.' if manual else ' Fermez le volet exposé pour limiter les apports solaires.'
        elif strong and 'heat' in needs and position != 100 and state != 'open':
            advice='open'
            tip=' Si le volet est fermé, ouvrez-le pour profiter du soleil.' if manual else ' Ouvrez le volet pour profiter du soleil.'
        elif sun is not None and sun.elevation < 0 and 'heat' in needs and position != 0 and state != 'closed':
            advice='close'
            tip=' Si le volet est ouvert, fermez-le pour protéger la pièce du froid nocturne.' if manual else ' Fermez le volet pour protéger la pièce du froid nocturne.'
        # The sun is about to reach the window of a room already too warm: close before, not after.
        start=_value(readings,'shutter_sun_start:'+eid) if driven else None
        soon=_soon(start,now)
        if (not advice and override is not True and soon is not None and front is not True and 'cool' in needs
                and position != 0 and state != 'closed'):
            advice='close'
            tip=f' Le soleil arrive sur la fenêtre à {soon} : fermez le volet avant.'
        if driven and override is not True:
            if driving:
                # It moves the cover itself: Hestia-FB does not ask the person to do it twice.
                advice,tip=None,f' {name} pilote le volet' + (f', position visée {target:g} %.' if target is not None else '.')
                if 'cool' in needs and climate is False:
                    tip += ' Son mode climat est coupé : il ne ferme pas contre la chaleur.'
            elif off and advice:
                tip += {'disabled':f' {name} est désactivé pour ce volet.','auto':f' Le pilotage automatique de {name} est coupé.',
                        'tracking':f' Le suivi du soleil de {name} est coupé.'}[off]
        message += tip
        if model == 'geometry': message += ' Ombre estimée par géométrie.'
        elif model == 'simple': message += ' Ombre estimée par modèle simple.'
        light=_value(readings,'illuminance')
        if light is not None and light < settings.illuminance_low:
            message += ' Luminosité intérieure faible ; elle ne prouve pas la position du volet.'
        result.append(dict(entity_id=eid,mode=meta.shutter,position=position,state=state,advice=advice,message=message,
                           shade_fraction=shade,shade_model=model,manual_override=override,automatic=automatic,
                           driving=driving,off=off,detection=detection,climate=climate,
                           cover=meta.cover_entity,driver=meta.driver,sun_front=front,target=target,
                           sun_start=start,soon=soon is not None and advice=='close' and front is not True,
                           reason=_value(readings,'shutter_reason:'+eid) if driven else None,
                           override_end=_value(readings,'shutter_override_end:'+eid) if driven else None,
                           sun_end=_value(readings,'shutter_sun_end:'+eid) if driven else None))
    return result


def _slope(history, now, window=30):
    if now is None or now.tzinfo is None:
        return None
    points={}
    for point in history or []:
        try:
            stamp,value=point
            stamp=datetime.fromisoformat(stamp.replace('Z','+00:00')) if isinstance(stamp,str) else stamp
            if stamp.tzinfo and _number(value) and now-timedelta(minutes=window) <= stamp <= now:
                points[stamp]=value
        except (ValueError,TypeError,AttributeError):
            continue
    values=sorted(points.items())
    if len(values)<3 or (values[-1][0]-values[0][0]).total_seconds()<600:
        return None
    xs=[(t-values[0][0]).total_seconds()/3600 for t,v in values]
    ys=[v for t,v in values]
    mx,my=sum(xs)/len(xs),sum(ys)/len(ys)
    denominator=sum((x-mx)**2 for x in xs)
    return round(sum((x-mx)*(y-my) for x,y in zip(xs,ys))/denominator,2) if denominator else None


# Below these speeds per hour a measure is « stable »: a sensor's own noise is no trend.
STEADY={'temperature':.3,'humidity':2,'co2':100,'voc':30,'pm25':3,'solar':40,'heating':10}


def _curve(history, now, key, window=30, step=2):
    """A measure's last half hour for its tile: its speed per hour, its way (up, down, stable) and its points.

    Points are the mean of each `step` minutes, as [minutes ago, value]; None under the same three measures over
    ten minutes the slope asks for.

    A sensor that reports only when its value moves stays silent while it is stable: its last value holds until now,
    and the last one before the window holds at its start. Silence is « stable », never a gap."""
    if now is None or now.tzinfo is None:
        return None
    start,points,before=now-timedelta(minutes=window),[],None
    for point in history or []:
        try:
            stamp,value=point
            stamp=datetime.fromisoformat(stamp.replace('Z','+00:00')) if isinstance(stamp,str) else stamp
            if not stamp.tzinfo or not _number(value) or stamp>now:
                continue
            if stamp<start:
                before=(start,float(value))
            else:
                points.append((stamp,float(value)))
        except (ValueError,TypeError,AttributeError):
            continue
    if before and (not points or points[0][0]>start):
        points.insert(0,before)
    if points and (now-points[-1][0]).total_seconds()>=step*60:
        points.append((now,points[-1][1]))
    slope=_slope(points,now,window)
    if slope is None:
        return None
    buckets={}
    for stamp,value in points:
        buckets.setdefault(min(int((now-stamp).total_seconds()/60//step),window//step-1),[]).append(value)
    points=[[min(window,k*step+step/2),round(sum(v)/len(v),2)] for k,v in sorted(buckets.items(),reverse=True)]
    way='stable' if abs(slope)<STEADY[key] else 'up' if slope>0 else 'down'
    return dict(slope=slope,way=way,points=points)


def features(readings,settings,context,openings,sun,details,needs,action,reason,now,ai,ae,air):
    ti,te=_value(readings,'indoor_temperature'),_value(readings,'outdoor_temperature')
    rh=_value(readings,'indoor_humidity')
    dew=None
    if ti is not None and rh is not None and rh>0:
        alpha=math.log(rh/100)+17.62*ti/(243.12+ti)
        dew=round(243.12*alpha/(17.62-alpha),1)
    glazing=context.get('glazing_factor',.7)
    glazing=glazing if _number(glazing) and 0<=glazing<=1 else .7
    glass=round(te+glazing*(ti-te),1) if ti is not None and te is not None else None
    from .assessment import absolute_humidity
    saturated=absolute_humidity(ti,100) if ti is not None else None
    incoming=round(ae/saturated*(273.15+te)/(273.15+ti)*100,1) if ae is not None and saturated and te is not None else None
    condensation=dew >= glass if dew is not None and glass is not None else None
    hmessage='Buée estimée à partir du point de rosée et d’un vitrage modélisé ; aucune condensation observée.'
    if ai is not None and ae is not None and ae>ai+1:
        hmessage+=' L’air extérieur risque de réhumidifier la pièce.'
    opened=[d['entity_id'] for d in details if d['open'] is True]
    minutes=context.get('opening_minutes') or {}
    # If even one open contact lacks a reliable transition, the room duration is unknown.
    elapsed=max(minutes[e] for e in opened) if opened and all(_number(minutes.get(e)) and minutes[e]>=0 for e in opened) else None
    from .wind import open_first, crossing
    candidates=opened if opened else open_first(details) if action == "ouvrir" else []
    capacities=[]
    for eid in candidates:
        e=openings.get(eid)
        if e is None:
            capacities.append(None)
            continue
        if _number(e.width) and _number(e.height) and e.width>0 and e.height>0:
            capacities.append(e.width*e.height*{'window':.6,'french':.8,'skylight':.25,'door':.8}.get(e.kind,.5))
        else:
            capacities.append(None)
    capacity=round(sum(capacities),2) if capacities and all(v is not None for v in capacities) else None
    duration=None
    if needs and (action=='ouvrir' or (opened and action=='ok')):
        middle=10
        if ti is not None and te is not None and abs(ti-te)>=8: middle=5
        selected=[dict(d,open=True) for d in details if d['entity_id'] in candidates]
        if crossing(selected) == 'wind': middle*=.75
        if capacity is not None: middle/=max(.5,min(2,capacity))
        if reason=='short_air_change': middle=min(middle,5)
        duration={'min':max(2,round(middle*.6)),'max':max(3,round(middle*1.5))}
    vm='Durée indicative avant réévaluation ; les mesures restent prioritaires, sans garantie de renouvellement complet.'
    if capacity is not None: vm+=' Capacité estimée en m² effectifs, avec hypothèse d’ouverture ; débit non mesuré.'
    if opened and elapsed is None: vm+=' Ouvert depuis une durée inconnue.'
    return dict(shutters=_shutters(readings,settings,openings,sun,details,needs,now),presence=_presence(readings,context),air=air,
                ventilation=dict(opened_minutes=elapsed,duration_minutes=duration,message=vm,capacity=capacity),
                humidity=dict(dew_point=dew,incoming_relative=incoming,glass_temperature=glass,condensation_risk=condensation,message=hmessage),
                trends=dict(indoor=_slope(context.get('temperature_history'),now),outdoor=_slope(context.get('outdoor_history'),now),window_minutes=30,
                            curves={k:_curve(context.get(k+'_history'),now,k) for k in STEADY},
                            message='Tendance en °C/h sur au plus 30 minutes de mesures réelles ; au moins 3 mesures sur 10 minutes.'))
