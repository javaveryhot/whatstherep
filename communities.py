settings = {
  "s": {
    "name": "Steam",
    "logo_url": "/static/images/community_icons/steam.png",
    "id_methods": [
      {
        "label": "SteamID",
        "regex": "^STEAM_[0-5]:[0-1]:[0-9]*$",
        "example": "STEAM_0:0:972338548",
        "mandatory": False,
        "permanent": True
      },
      {
        "label": "SteamID3",
        "regex": r"^\[U:[10]:[0-9]+\]$",
        "example": "[U:1:17433806]",
        "mandatory": False,
        "permanent": True
      },
      {
        "label": "SteamID64",
        "regex": "^\d{17}$",
        "example": "76561198072423639",
        "mandatory": True,
        "permanent": True
      },
      {
        "label": "CustomURL",
        "regex": "^[A-Za-z_0-9]+$",
        "example": "the_crunchy_frog",
        "mandatory": False,
        "permanent": False
      }
    ],
    "tags": [
      "Scammer",
      "Griefer",
      "Smurf",
      "Cheater",
      "Toxic",
      "Good teammate"
    ]
  },

  "d": {
    "name": "Discord",
    "logo_url": "/static/images/community_icons/discord.png",
    "id_methods": [
      {
        "label": "Username",
        "regex": "^.{3,32}#[0-9]{4}$",
        "example": "a_gecko#6832",
        "mandatory": False,
        "permanent": False
      },
      {
        "label": "User ID",
        "regex": "^[0-9]{18}$",
        "example": "802207192990605313",
        "mandatory": True,
        "permanent": True
      }
    ],
    "tags": [
      "Scammer",
      "Bot/Spammer/Griefer",
      "Friendly"
    ]
  },

  "r": {
    "name": "Reddit",
    "logo_url": "/static/images/community_icons/reddit.png",
    "id_methods": [
      {
        "label": "Username",
        "regex": "^[A-Za-z0-9_-]+$",
        "example": "the_crunchy_frog",
        "mandatory": True,
        "permanent": True
      }
    ],
    "tags": [
      "Scammer",
      "Bot/Spammer"
    ]
  },

  "t": {
    "name": "Twitter",
    "logo_url": "/static/images/community_icons/twitter.png",
    "id_methods": [
      {
        "label": "Username/Handle",
        "regex": "^[A-Za-z0-9_]{4,15}$",
        "example": "the_crunchy_frog",
        "mandatory": True,
        "permanent": False
      }
    ],
    "tags": [
      "Scammer",
      "Bot/Spammer"
    ]
  }
}