"""Constants for the Local OpenAI LLM integration."""

import logging
import re
from typing import Literal

from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT
from homeassistant.helpers import llm

DOMAIN = "local_openai"
LOGGER = logging.getLogger(__package__)

CONF_RECOMMENDED = "recommended"
CONF_BASE_URL = "base_url"
CONF_SERVER_NAME = "server_name"
CONF_STRIP_EMOJIS = "strip_emojis"
CONF_STRIP_EMPHASIS = "strip_emphasis"
CONF_STRIP_LATEX = "strip_latex"
CONF_MANUAL_PROMPTING = "manual_prompting"
CONF_TEMPERATURE = "temperature"
CONF_PARALLEL_TOOL_CALLS = "parallel_tool_calls"
CONF_GENERATE_DATA = "generate_data"
CONF_GENERATE_IMAGE = "generate_image"
CONF_SUPPORT_ATTACHMENTS = "support_attachments"

RECOMMENDED_CONVERSATION_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
}

MAX_TOOL_ITERATIONS = 10

AUDIO_MIME_TYPE_MAP: dict[str, Literal["mp3", "wav"]] = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mpeg3": "mp3",
    "audio/x-mpeg-3": "mp3",
    "audio/x-mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/vnd.wave": "wav",
}

LATEX_MATH_SPAN = re.compile(
    r"""
    \$\$[\s\S]+?\$\$
  | \$(?!\s)[^$\n]+?(?<!\s)\$
  | \\\([^)]*\\\)
  | \\\[[^]]*\\]
    """,
    re.VERBOSE,
)

GEMINI_MIME_TYPES_SUPPORTED = (
    "application/dart",
    "application/ecmascript",
    "application/gzip",
    "application/json",
    "application/msword",
    "application/pdf",
    "application/protobuf",
    "application/typescript",
    "application/vnd.apache.parquet",
    "application/vnd.curl",
    "application/vnd.ibm.secure-container",
    "application/vnd.jupyter",
    "application/vnd.ms-excel",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    "application/x-csh",
    "application/x-hwp",
    "application/x-latex",
    "application/x-php",
    "application/x-powershell",
    "application/x-sh",
    "application/x-zsh",
    "application/xml",
    "application/zip",
    "audio/G722",
    "audio/L16",
    "audio/MP4A-LATM",
    "audio/aac",
    "audio/adts",
    "audio/aiff",
    "audio/amr",
    "audio/g723",
    "audio/iLBC",
    "audio/m4a",
    "audio/mpeg",
    "audio/ogg",
    "audio/pcm",
    "audio/wav",
    "audio/x-ac3",
    "audio/x-adpcm",
    "audio/x-caf",
    "audio/x-dca",
    "audio/x-eac3",
    "audio/x-flac",
    "audio/x-gsm",
    "audio/x-oma",
    "audio/x-speex",
    "audio/x-tta",
    "audio/x-voc",
    "audio/x-wavpack",
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/tiff",
    "image/webp",
    "image/x-adobe-dng",
    "text/cache-manifest",
    "text/calendar",
    "text/css",
    "text/csv",
    "text/dns",
    "text/html",
    "text/javascript",
    "text/jsx",
    "text/markdown",
    "text/plain",
    "text/provenance-notation",
    "text/rtf",
    "text/sgml",
    "text/shaclc",
    "text/shex",
    "text/spdx",
    "text/tab-separated-values",
    "text/texmacs",
    "text/troff",
    "text/tsx",
    "text/turtle",
    "text/uri-list",
    "text/vcard",
    "text/vnd.graphviz",
    "text/vnd.in3d.3dml",
    "text/vnd.in3d.spot",
    "text/vnd.sun.j2me.app-descriptor",
    "text/vnd.wap.wml",
    "text/vnd.wap.wmlscript",
    "text/vtt",
    "text/wgsl",
    "text/x-asm",
    "text/x-bibtex",
    "text/x-boo",
    "text/x-c++hdr",
    "text/x-c++src",
    "text/x-cassandra",
    "text/x-chdr",
    "text/x-coffeescript",
    "text/x-component",
    "text/x-csharp",
    "text/x-csrc",
    "text/x-cuda",
    "text/x-d",
    "text/x-diff",
    "text/x-emacs-lisp",
    "text/x-erlang",
    "text/x-gff3",
    "text/x-go",
    "text/x-haskell",
    "text/x-java-properties",
    "text/x-java-source",
    "text/x-kotlin",
    "text/x-lilypond",
    "text/x-lisp",
    "text/x-literate-haskell",
    "text/x-lua",
    "text/x-moc",
    "text/x-objcsrc",
    "text/x-pascal",
    "text/x-perl",
    "text/x-perl-script",
    "text/x-python-script",
    "text/x-r-markdown",
    "text/x-rsrc",
    "text/x-rst",
    "text/x-ruby-script",
    "text/x-rust",
    "text/x-sass",
    "text/x-scala",
    "text/x-scheme",
    "text/x-scss",
    "text/x-setext",
    "text/x-sfv",
    "text/x-siesta",
    "text/x-sos",
    "text/x-sql",
    "text/x-swift",
    "text/x-tcl",
    "text/x-tex",
    "text/x-vbasic",
    "text/x-vcalendar",
    "text/yaml",
    "video/3gpp",
    "video/3gpp2",
    "video/avi",
    "video/mp4",
    "video/mpeg",
    "video/mpg",
    "video/quicktime",
    "video/webm",
    "video/x-flv",
    "video/x-m4v",
    "video/x-matroska",
    "video/x-ms-wmv",
)
