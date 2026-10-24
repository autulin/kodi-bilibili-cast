"""UPnP device description and service descriptions.

The NirvanaControl SCPD is derived from the MIT-licensed Macast nirvana
plugin. See THIRD_PARTY_NOTICES.md in the repository root.
"""

from xml.sax.saxutils import escape

NVA_SERVICE_TYPE = "urn:app-bilibili-com:service:NirvanaControl:3"
NVA_SERVICE_ID = "urn:app-bilibili-com:serviceId:NirvanaControl"

NVA_SCPD = """<?xml version="1.0" encoding="UTF-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <actionList>
    <action>
      <name>GetAppInfo</name>
      <argumentList>
        <argument>
          <name>PackageName</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_PackageName</relatedStateVariable>
        </argument>
        <argument>
          <name>AppKey</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_AppKey</relatedStateVariable>
        </argument>
        <argument>
          <name>Signature</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_Signature</relatedStateVariable>
        </argument>
        <argument>
          <name>CurrentSignedIn</name>
          <direction>out</direction>
          <relatedStateVariable>SignedIn</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>LoginWithCode</name>
      <argumentList>
        <argument>
          <name>Code</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>PrepareForMirrorProjection</name>
      <argumentList>
        <argument>
          <name>ScreenWidth</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_ScreenResolution</relatedStateVariable>
        </argument>
        <argument>
          <name>ScreenHeight</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_ScreenResolution</relatedStateVariable>
        </argument>
        <argument>
          <name>PushUrl</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>SetDanmakuSwitch</name>
      <argumentList>
        <argument>
          <name>DesiredSwitch</name>
          <direction>in</direction>
          <relatedStateVariable>DanmakuSwitch</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>AppendDanmaku</name>
      <argumentList>
        <argument>
          <name>Content</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
        <argument>
          <name>Size</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
        <argument>
          <name>Type</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
        <argument>
          <name>Color</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
        <argument>
          <name>DanmakuId</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
        <argument>
          <name>Action</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>GetPlayInfo</name>
      <argumentList>
        <argument>
          <name>Params</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
        <argument>
          <name>Content</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>GetAccountInfo</name>
      <argumentList>
        <argument>
          <name>VipInfo</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>SwitchQuality</name>
      <argumentList>
        <argument>
          <name>Qn</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
  </actionList>
  <serviceStateTable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_UnlimitedString</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_PackageName</name>
      <dataType>string</dataType>
      <defaultValue>com.xiaodianshi.tv.yst</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_AppKey</name>
      <dataType>string</dataType>
      <defaultValue>0000000000000000</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_Signature</name>
      <dataType>string</dataType>
      <defaultValue>0000000000000000</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_UnlimitedInt</name>
      <dataType>i4</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_ScreenResolution</name>
      <dataType>ui4</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>SignedIn</name>
      <dataType>boolean</dataType>
      <defaultValue>1</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>DanmakuSwitch</name>
      <dataType>boolean</dataType>
    </stateVariable>
  </serviceStateTable>
</scpd>
"""


def _action(name, args):
    if not args:
        return "    <action><name>%s</name></action>" % escape(name)
    rows = ["    <action>", "      <name>%s</name>" % escape(name),
            "      <argumentList>"]
    for arg_name, direction, state in args:
        rows.extend([
            "        <argument>",
            "          <name>%s</name>" % escape(arg_name),
            "          <direction>%s</direction>" % direction,
            "          <relatedStateVariable>%s</relatedStateVariable>" % escape(state),
            "        </argument>",
        ])
    rows.extend(["      </argumentList>", "    </action>"])
    return "\n".join(rows)


def _state(name, data_type, allowed=None, default=None):
    rows = ["    <stateVariable sendEvents=\"no\">",
            "      <name>%s</name>" % escape(name),
            "      <dataType>%s</dataType>" % escape(data_type)]
    if allowed:
        rows.append("      <allowedValueList>")
        for value in allowed:
            rows.append("        <allowedValue>%s</allowedValue>" % escape(value))
        rows.append("      </allowedValueList>")
    if default is not None:
        rows.append("      <defaultValue>%s</defaultValue>" % escape(str(default)))
    rows.append("    </stateVariable>")
    return "\n".join(rows)


def _build_scpd(actions, states):
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<scpd xmlns="urn:schemas-upnp-org:service-1-0">',
        "  <specVersion><major>1</major><minor>0</minor></specVersion>",
        "  <actionList>",
        "\n".join(_action(name, args) for name, args in actions),
        "  </actionList>",
        "  <serviceStateTable>",
        "\n".join(_state(*state) for state in states),
        "  </serviceStateTable>",
        "</scpd>",
    ])


_AV_ACTIONS = [
    ("SetAVTransportURI", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("CurrentURI", "in", "AVTransportURI"),
        ("CurrentURIMetaData", "in", "AVTransportURIMetaData"),
    ]),
    ("SetNextAVTransportURI", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("NextURI", "in", "NextAVTransportURI"),
        ("NextURIMetaData", "in", "NextAVTransportURIMetaData"),
    ]),
    ("GetTransportInfo", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("CurrentTransportState", "out", "TransportState"),
        ("CurrentTransportStatus", "out", "TransportStatus"),
        ("CurrentSpeed", "out", "TransportPlaySpeed"),
    ]),
    ("GetPositionInfo", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Track", "out", "CurrentTrack"),
        ("TrackDuration", "out", "CurrentTrackDuration"),
        ("TrackMetaData", "out", "CurrentTrackMetaData"),
        ("TrackURI", "out", "CurrentTrackURI"),
        ("RelTime", "out", "RelativeTimePosition"),
        ("AbsTime", "out", "AbsoluteTimePosition"),
        ("RelCount", "out", "RelativeCounterPosition"),
        ("AbsCount", "out", "AbsoluteCounterPosition"),
    ]),
    ("GetMediaInfo", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("NrTracks", "out", "NumberOfTracks"),
        ("MediaDuration", "out", "CurrentMediaDuration"),
        ("CurrentURI", "out", "AVTransportURI"),
        ("CurrentURIMetaData", "out", "AVTransportURIMetaData"),
        ("NextURI", "out", "NextAVTransportURI"),
        ("NextURIMetaData", "out", "NextAVTransportURIMetaData"),
        ("PlayMedium", "out", "PlaybackStorageMedium"),
        ("RecordMedium", "out", "RecordStorageMedium"),
        ("WriteStatus", "out", "RecordMediumWriteStatus"),
    ]),
    ("GetDeviceCapabilities", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("PlayMedia", "out", "PossiblePlaybackStorageMedia"),
        ("RecMedia", "out", "PossibleRecordStorageMedia"),
        ("RecQualityModes", "out", "PossibleRecordQualityModes"),
    ]),
    ("GetTransportSettings", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("PlayMode", "out", "CurrentPlayMode"),
        ("RecQualityMode", "out", "CurrentRecordQualityMode"),
    ]),
    ("Play", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Speed", "in", "TransportPlaySpeed"),
    ]),
    ("Pause", [("InstanceID", "in", "A_ARG_TYPE_InstanceID")]),
    ("Stop", [("InstanceID", "in", "A_ARG_TYPE_InstanceID")]),
    ("Seek", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Unit", "in", "A_ARG_TYPE_SeekMode"),
        ("Target", "in", "A_ARG_TYPE_SeekTarget"),
    ]),
]

_AV_STATES = [
    ("A_ARG_TYPE_InstanceID", "ui4"),
    ("TransportState", "string",
     ["STOPPED", "PLAYING", "PAUSED_PLAYBACK", "TRANSITIONING", "NO_MEDIA_PRESENT"],
     "STOPPED"),
    ("TransportStatus", "string", ["OK", "ERROR_OCCURRED"], "OK"),
    ("TransportPlaySpeed", "string", ["0.5", "0.75", "1", "1.25", "1.5", "2"], "1"),
    ("CurrentTrack", "ui4", None, 0),
    ("CurrentTrackDuration", "string", None, "00:00:00"),
    ("CurrentTrackMetaData", "string"),
    ("CurrentTrackURI", "string"),
    ("RelativeTimePosition", "string", None, "00:00:00"),
    ("AbsoluteTimePosition", "string", None, "00:00:00"),
    ("RelativeCounterPosition", "i4", None, 0),
    ("AbsoluteCounterPosition", "i4", None, 0),
    ("NumberOfTracks", "ui4", None, 0),
    ("CurrentMediaDuration", "string", None, "00:00:00"),
    ("AVTransportURI", "string"),
    ("AVTransportURIMetaData", "string"),
    ("NextAVTransportURI", "string"),
    ("NextAVTransportURIMetaData", "string"),
    ("PlaybackStorageMedium", "string", ["NONE", "NETWORK"], "NONE"),
    ("RecordStorageMedium", "string", ["NOT_IMPLEMENTED"], "NOT_IMPLEMENTED"),
    ("PossiblePlaybackStorageMedia", "string", None, "NETWORK"),
    ("PossibleRecordStorageMedia", "string", None, "NOT_IMPLEMENTED"),
    ("PossibleRecordQualityModes", "string", None, "NOT_IMPLEMENTED"),
    ("CurrentPlayMode", "string", ["NORMAL"], "NORMAL"),
    ("CurrentRecordQualityMode", "string", ["NOT_IMPLEMENTED"], "NOT_IMPLEMENTED"),
    ("RecordMediumWriteStatus", "string", ["NOT_IMPLEMENTED"], "NOT_IMPLEMENTED"),
    ("A_ARG_TYPE_SeekMode", "string", ["REL_TIME", "TRACK_NR"], "REL_TIME"),
    ("A_ARG_TYPE_SeekTarget", "string"),
]

_RC_ACTIONS = [
    ("GetVolume", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Channel", "in", "A_ARG_TYPE_Channel"),
        ("CurrentVolume", "out", "Volume"),
    ]),
    ("SetVolume", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Channel", "in", "A_ARG_TYPE_Channel"),
        ("DesiredVolume", "in", "Volume"),
    ]),
    ("GetMute", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Channel", "in", "A_ARG_TYPE_Channel"),
        ("CurrentMute", "out", "Mute"),
    ]),
    ("SetMute", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("Channel", "in", "A_ARG_TYPE_Channel"),
        ("DesiredMute", "in", "Mute"),
    ]),
    ("ListPresets", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("CurrentPresetNameList", "out", "PresetNameList"),
    ]),
    ("SelectPreset", [
        ("InstanceID", "in", "A_ARG_TYPE_InstanceID"),
        ("PresetName", "in", "A_ARG_TYPE_PresetName"),
    ]),
]

_RC_STATES = [
    ("A_ARG_TYPE_InstanceID", "ui4"),
    ("A_ARG_TYPE_Channel", "string", ["Master"], "Master"),
    ("Volume", "ui2", None, 50),
    ("Mute", "boolean", None, 0),
    ("PresetNameList", "string", None, "FactoryDefaults"),
    ("A_ARG_TYPE_PresetName", "string", ["FactoryDefaults"], "FactoryDefaults"),
]

_CM_ACTIONS = [
    ("GetProtocolInfo", [
        ("Source", "out", "SourceProtocolInfo"),
        ("Sink", "out", "SinkProtocolInfo"),
    ]),
    ("GetCurrentConnectionIDs", [
        ("ConnectionIDs", "out", "CurrentConnectionIDs"),
    ]),
    ("GetCurrentConnectionInfo", [
        ("ConnectionID", "in", "A_ARG_TYPE_ConnectionID"),
        ("RcsID", "out", "A_ARG_TYPE_RcsID"),
        ("AVTransportID", "out", "A_ARG_TYPE_AVTransportID"),
        ("ProtocolInfo", "out", "A_ARG_TYPE_ProtocolInfo"),
        ("PeerConnectionManager", "out", "A_ARG_TYPE_ConnectionManager"),
        ("PeerConnectionID", "out", "A_ARG_TYPE_ConnectionID"),
        ("Direction", "out", "A_ARG_TYPE_Direction"),
        ("Status", "out", "A_ARG_TYPE_ConnectionStatus"),
    ]),
]

_CM_STATES = [
    ("SourceProtocolInfo", "string", None, ""),
    ("SinkProtocolInfo", "string", None,
     "http-get:*:video/mp4:*,http-get:*:video/x-matroska:*,http-get:*:video/mpeg:*"),
    ("CurrentConnectionIDs", "string", None, "0"),
    ("A_ARG_TYPE_ConnectionStatus", "string",
     ["OK", "ContentFormatMismatch", "InsufficientBandwidth", "UnreliableChannel", "Unknown"],
     "OK"),
    ("A_ARG_TYPE_ConnectionManager", "string"),
    ("A_ARG_TYPE_Direction", "string", ["Input", "Output"], "Output"),
    ("A_ARG_TYPE_ProtocolInfo", "string"),
    ("A_ARG_TYPE_ConnectionID", "i4", None, 0),
    ("A_ARG_TYPE_AVTransportID", "i4", None, 0),
    ("A_ARG_TYPE_RcsID", "i4", None, 0),
]


def minimal_scpd(service):
    if service == "AVTransport":
        return _build_scpd(_AV_ACTIONS, _AV_STATES)
    if service == "RenderingControl":
        return _build_scpd(_RC_ACTIONS, _RC_STATES)
    if service == "ConnectionManager":
        return _build_scpd(_CM_ACTIONS, _CM_STATES)
    return NVA_SCPD


class DeviceInfo:
    def __init__(self, uuid, friendly_name="我的小电视", version="0.1.0"):
        self.uuid = uuid
        self.friendly_name = friendly_name
        self.version = version

    @property
    def udn(self):
        return "uuid:" + self.uuid

    def description_xml(self):
        friendly_name = escape(self.friendly_name).replace("{", "{{").replace("}", "}}")
        uuid = self.uuid
        return """<?xml version="1.0" encoding="UTF-8"?>
<root configId="1" xmlns:dlna="urn:schemas-dlna-org:device-1-0"
      xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
    <UDN>uuid:{uuid}</UDN>
    <friendlyName>{friendly_name}</friendlyName>
    <manufacturer>Bilibili Inc.</manufacturer>
    <manufacturerURL>https://bilibili.com/</manufacturerURL>
    <modelDescription>云视听小电视</modelDescription>
    <modelName>Kodi</modelName>
    <modelNumber>1024</modelNumber>
    <modelURL>https://app.bilibili.com/</modelURL>
    <serialNumber>1024</serialNumber>
    <X_brandName>Kodi</X_brandName>
    <hostVersion>25</hostVersion>
    <ottVersion>106400</ottVersion>
    <channelName>master</channelName>
    <capability>254</capability>
    <dlna:X_DLNADOC xmlns:dlna="urn:schemas-dlna-org:device-1-0">DMR-1.50</dlna:X_DLNADOC>
    <dlna:X_DLNACAP xmlns:dlna="urn:schemas-dlna-org:device-1-0">playcontainer-1-0</dlna:X_DLNACAP>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
        <SCPDURL>/bilibili/AVTransport/{uuid}/scpd.xml</SCPDURL>
        <controlURL>/bilibili/AVTransport/{uuid}/control.xml</controlURL>
        <eventSubURL>/bilibili/AVTransport/{uuid}/event.xml</eventSubURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId>
        <SCPDURL>/bilibili/RenderingControl/{uuid}/scpd.xml</SCPDURL>
        <controlURL>/bilibili/RenderingControl/{uuid}/control.xml</controlURL>
        <eventSubURL>/bilibili/RenderingControl/{uuid}/event.xml</eventSubURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
        <SCPDURL>/bilibili/ConnectionManager/{uuid}/scpd.xml</SCPDURL>
        <controlURL>/bilibili/ConnectionManager/{uuid}/control.xml</controlURL>
        <eventSubURL>/bilibili/ConnectionManager/{uuid}/event.xml</eventSubURL>
      </service>
      <service>
        <serviceType>{nva_type}</serviceType>
        <serviceId>{nva_id}</serviceId>
        <SCPDURL>/bilibili/NirvanaControl/{uuid}/scpd.xml</SCPDURL>
        <controlURL>/bilibili/NirvanaControl/{uuid}/control.xml</controlURL>
        <eventSubURL>/bilibili/NirvanaControl/{uuid}/event.xml</eventSubURL>
      </service>
    </serviceList>
  </device>
</root>
""".format(
            uuid=uuid,
            friendly_name=friendly_name,
            nva_type=NVA_SERVICE_TYPE,
            nva_id=NVA_SERVICE_ID,
        )
