"""
Support for interface with a Cambridge Audio Azur 851N media player.

For more details about this platform, please refer to the documentation at
https://github.com/ninjalf2/cambridge_851n
"""
import json
import logging
import urllib.request
import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_IDLE,
    STATE_STANDBY
)

__version__ = "0.5"

_LOGGER = logging.getLogger(__name__)

SUPPORT_851N = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.REPEAT_SET
)

SUPPORT_851N_PREAMP = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.REPEAT_SET
)

DEFAULT_NAME = "Cambridge Audio Azur 851N"
DEVICE_CLASS = "receiver"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(hass, config, add_devices, discovery_info=None):
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)

    if host is None:
        _LOGGER.error("No Cambridge Audio Azur 851N IP address found in configuration file")
        return

    add_devices([Cambridge851NDevice(host, name)])


class Cambridge851NDevice(MediaPlayerEntity):
    def __init__(self, host, name):
        _LOGGER.info("Setting up Cambridge Audio Azur 851N")
        self._host = host
        self._max_volume = 100
        self._mediasource = ""
        self._min_volume = 0
        self._muted = False
        self._name = name
        self._pwstate = "NETWORK"
        self._should_setup_sources = True
        self._source_list = {}
        self._source_list_reverse = {}
        self._state = STATE_OFF
        self._volume = 0
        self._artwork_url = None
        self._preamp_mode = False
        self._shuffle_mode = "off"
        self._repeat_mode = "off"
        self._media_title = None
        self._media_artist = None
        self._media_album_name = None
        self._media_duration = None

        _LOGGER.debug( "Set up Cambridge Audio Azur 851N with IP: %s", host)

    def _setup_sources(self):
        if self._should_setup_sources:
            _LOGGER.debug("Setting up Cambridge Audio Azur 851N sources")
            sources = json.loads(self._command("/smoip/system/sources"))["data"]
            sources2 = sources.get("sources")
            self._source_list = {}
            self._source_list_reverse = {}

            for i in sources2:
                _LOGGER.debug("Setting up Cambridge Audio Azur 851N sources... %s", i["id"])
                source = i["id"]
                configured_name = i["name"]
                self._source_list[source] = configured_name
                self._source_list_reverse[configured_name] = source

            presets = json.loads(self._command("/smoip/presets/list"))["data"]
            presets2 = presets.get("presets")
            for i in presets2:
                _LOGGER.debug("Setting up Cambridge Audio Azur 851N sources... %s", i["id"])
                source = str(i["id"])
                configured_name = i["name"]
                self._source_list[source] = configured_name
                self._source_list_reverse[configured_name] = source

        self._should_setup_sources = False

    def set_shuffle(self, shuffle):
        action = "off"
        if shuffle:
            action = "all"

        self._command("/smoip/zone/play_control?mode_shuffle=" + action)

    def set_repeat(self, repeat):
        adjrepeat = repeat
        if repeat == "one":
            adjrepeat = "toggle"

        self._command("/smoip/zone/play_control?mode_repeat=" + adjrepeat)

    def media_play_pause(self):
        self._command("/smoip/zone/play_control?action=toggle")

    def media_pause(self):
        self._command("/smoip/zone/play_control?action=pause")

    def media_stop(self):
        self._command("/smoip/zone/play_control?action=stop")

    def media_play(self):
        if self.state == STATE_PAUSED:
            self.media_play_pause()

    def media_next_track(self):
        self._command("/smoip/zone/play_control?skip_track=1")

    def media_previous_track(self):
        self._command("/smoip/zone/play_control?skip_track=-1")

    def update(self):
        powerstate = self._getPowerState()
        self._pwstate = powerstate["data"]["power"]

        zonestate = self._getZoneState()
        zonestatedata = zonestate["data"]

        self._preamp_mode = zonestatedata["pre_amp_mode"]
        self._mediasource = zonestatedata["source"]

        if self._preamp_mode:
            self._muted = zonestatedata["mute"]
            self._volume = zonestatedata["volume_percent"] / 100
        else:
            self._muted = False
            self._volume = None

        playstate = self._getPlayState()
        playstatedata = playstate["data"]
        self._state = playstatedata["state"]

        try:
            playstatemetadata = playstatedata["metadata"]

            self._media_title = playstatemetadata["title"]
            self._media_artist = playstatemetadata["artist"]
            self._artwork_url = playstatemetadata["art_url"]
            self._media_album_name = playstatemetadata["album"]
            self._media_duration = playstatemetadata["duration"]
        except:
            self._media_artist = None
            self._media_title = None
            self._artwork_url = None
            self._media_album_name = None
            self._media_duration = None

        try:
            self._shuffle_mode = playstatedata["mode_shuffle"]
            self._repeat_mode = playstatedata["mode_repeat"]
        except:
            self._shuffle_mode = "off"
            self._repeat_mode = "off"

        self._setup_sources()

    def _getZoneState(self):
        return json.loads(self._command("/smoip/zone/state"))

    def _getPlayState(self):
        return json.loads(self._command("/smoip/zone/play_state"))

    def _getPowerState(self):
        return json.loads(self._command("/smoip/system/power"))

    def _command(self, command):
        """Establish a telnet connection and sends `command`."""
        _LOGGER.debug("Sending command: %s", command)
        return urllib.request.urlopen("http://" + self._host + command).read()

    @property
    def is_volume_muted(self):
        return self._muted

    @property
    def name(self):
        return self._name

    @property
    def source_list(self):
        return sorted(list(self._source_list.values()))

    @property
    def state(self):
        if self._pwstate == "NETWORK":
            return STATE_OFF
        if self._pwstate == "ON":
            if self._state == "play":
                return STATE_PLAYING
            elif self._state == "pause":
                return STATE_PAUSED
            elif self._state == "stop":
                return STATE_IDLE
            else:
                return STATE_ON
        return None

    @property
    def supported_features(self):
        if self._preamp_mode:
            return SUPPORT_851N_PREAMP
        return SUPPORT_851N

    @property
    def media_duration(self):
        return self._media_duration

    @property
    def media_album_name(self):
        return self._media_album_name

    @property
    def media_title(self):
        return self._media_title

    @property
    def media_artist(self):
        return self._media_artist

    @property
    def media_image_url(self):
        _LOGGER.debug("Cambridge Audio Azur 851N Artwork URL: %s", self._artwork_url)
        return self._artwork_url

    @property
    def volume_level(self):
        return self._volume

    def mute_volume(self, mute):
        self._command("/smoip/zone/state?mute=" + ("true" if mute else "false"))

    @property
    def source(self):
        return self._source_list[self._mediasource]

    @property
    def device_class(self):
        return DEVICE_CLASS

    @property
    def shuffle(self):
        return (self._shuffle_mode != "off")

    @property
    def repeat(self):
        return self._repeat_mode

    def mute_volume(self, mute):
        self._command("/smoip/zone/state?mute=" + ("true" if mute else "false"))

    def select_source(self, source):
        reverse_source = self._source_list_reverse[source]
        if reverse_source in [
            "AIRPLAY",
            "CAST",
            "IR",
            "MEDIA_PLAYER",
            "SPDIF_COAX",
            "SPDIF_TOSLINK",
            "SPOTIFY",
            "USB_AUDIO",
            "ROON"
        ]:
            self._command("/smoip/zone/state?source=" + reverse_source)
        else:
            self._command("/smoip/zone/recall_preset?preset=" + reverse_source)

    def set_volume_level(self, volume):
        vol_str = "/smoip/zone/state?volume_percent=" + str(int(volume * 100))
        self._command(vol_str)

    def turn_on(self):
        self._command("/smoip/system/power?power=ON")

    def turn_off(self):
        self._command("/smoip/system/power?power=NETWORK")

    def volume_up(self):
        self._command("/smoip/zone/state?volume_step_change=+1")

    def volume_down(self):
        self._command("/smoip/zone/state?volume_step_change=-1")
