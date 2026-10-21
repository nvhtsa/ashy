window.SITE = {
  lastfm: { user: "ashylmao", apiKey: "acb226da5cf87113c09f9253d8b68a7c" },

  playlist: [
    { title: "TORN – Ramzoid", src: "assets/media/track1.mp3" },
    { title: "JUST TOUCHED DOWN – Westwood", src: "assets/media/track2.mp3" },
    { title: "LIVING IN MY HEAD – Friz", src: "assets/media/track3.mp3" },
    { title: "puke! - Chris Miles", src: "assets/media/track4.mp3" },
    { title: "DENNIS TYPE BEAT - hooligan chase", src: "assets/media/track5.mp3" }
  ],

  socials: [
    { name: "Twitch", icon: "twitch", url: "https://twitch.tv/suckers" },
    { name: "YouTube", icon: "youtube", url: "https://youtube.com/@ashtyn" },
    { name: "TikTok", icon: "tiktok", url: "https://tiktok.com/@disaster" },
    { name: "X", icon: "x", url: "https://x.com/ashtynfps" },
    { name: "SoundCloud", icon: "soundcloud", url: "https://soundcloud.com/ashy" },
  ],

  gear: [
    { group: "PC", items: [
      ["CPU", "AMD Ryzen 7 3800X"], ["GPU", "GeForce RTX 4060 8 GB"], ["Memory", "Vulcan Z 32 GB DDR4 3600MHz"],
      ["Storage", "WD_Black 1TB NVME, Samsung 870 EVO 2TB"], ["Case", "Montech X3 Mesh"]
    ]},
    { group: "Displays", items: [
      ["Main monitor", "GIGABYTE 27in 1440P 300Hz"],
      ["Second monitor", "Sceptre C305B 30in 200 Hz"]
    ]},
    { group: "Peripherals", items: [
      ["Mouse", "Logitech PRO X Superlight 2 [1800 DPI, 1.68 > CS2"], ["Keyboard", "Wooting 60HE+"],
      ["Mousepad", "Superglide​ XL Glass ​Mousepad"], ["Headset", "HyperX Cloud II"], ["Microphone", "FIFINE K688"]
    ]}
  ],

  settings: [
    { group: "Counter-Strike 2", items: [
      ["Sensitivity", "1.68"], ["DPI", "1800"], ["eDPI", "3024"],
      ["Resolution", "1568x1050 stretched"]
    ], blocks: [
      { label: "Crosshair code", text: "CSxSM9W3OnxpoXUnDD9RD3Nc3rxW5J5PcqqkKu6qAccEPJ" },
      { label: "Launch options", text: "-exec autoexec.cfg -noreflex -high -novid" },
      { label: "autoexec.cfg", text: `r_show_build_info FALSE


//lj jb keys
bind mouse5 +ljright


setinfo jump 0; toggle jump "-999 0 0"
reset

//
alias jbn "-duck; bind mouse_x jb1"
alias jb1 "+jump; bind mouse_x jb2"
alias jb2 "-jump; revert"
alias revert "bind mouse_x yaw"


// ljright
alias reset "bind mouse_x yaw"
alias minusforward2 "-w; bind mouse_x "plusright""
alias plusright "+d; reset"

alias +ljright "+duck; bind mouse_x ljr1"
alias -ljright "-duck; bind mouse_x ljr2"

alias ljr1 "+jump; "bind mouse_x minusforward2"
alias ljr2 "-jump; "bind mouse_x"; reset


setinfo jump 0; toggle jump "-999 0 0"
reset

// jbn
alias jbn "-duck; bind mouse_x jb1"
alias jb1 "+jump; bind mouse_x jb2"
alias jb2 "-jump; revert"
alias revert "bind mouse_x yaw"` }
    ]},
  ]
};
