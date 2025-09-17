{ pkgs }: {
  deps = [
    pkgs.python311Full
    pkgs.replitPackages.prybar-python311
    pkgs.replitPackages.stderred
    pkgs.replitPackages.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.python311Packages.virtualenv
    
    # System dependencies for image processing
    pkgs.tesseract
    pkgs.imagemagick
    pkgs.ffmpeg
    pkgs.poppler_utils
    
    # Audio processing dependencies
    pkgs.portaudio
    pkgs.flac
    
    # Development tools
    pkgs.git
    pkgs.curl
    pkgs.wget
    
    # Database support
    pkgs.sqlite
    
    # Additional utilities
    pkgs.tree
    pkgs.htop
  ];
  
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.glib
      pkgs.xorg.libX11
    ];
    PYTHONHOME = "${pkgs.python311Full}";
    PYTHONBIN = "${pkgs.python311Full}/bin/python3.11";
    LANG = "en_US.UTF-8";
    STDERREDBIN = "${pkgs.replitPackages.stderred}/bin/stderred";
    PRYBAR_PYTHON_BIN = "${pkgs.replitPackages.prybar-python311}/bin/prybar-python311";
  };
}

