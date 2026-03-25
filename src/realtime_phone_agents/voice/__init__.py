from realtime_phone_agents.voice.effects.keyboard import KeyboardEffect
from realtime_phone_agents.voice.effects.ringback import RingbackEffect


def get_sound_effect(effect_type: type | None = None):
    """
    Create and return a sound effect instance.

    Args:
        effect_type: The type of effect to create. Defaults to KeyboardEffect.

    Returns:
        An instance of the specified effect type.
    """
    effect_type = effect_type or KeyboardEffect
    return effect_type()


def get_ringback_effect(effect_type: type | None = None, **kwargs):
    """Create and return a ringback effect instance."""
    effect_type = effect_type or RingbackEffect
    return effect_type(**kwargs)
