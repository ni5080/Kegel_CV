"""Videoquellen."""

from .source import (
    VideoSource, VideoInfo, Frame, FrameBuffer, VideoSourceError,
)
from .file_source import FileVideoSource, list_videos
from .stream_source import StreamVideoSource
from .factory import open_source, is_stream, source_label

__all__ = [
    "VideoSource", "VideoInfo", "Frame", "FrameBuffer", "VideoSourceError",
    "FileVideoSource", "list_videos", "StreamVideoSource",
    "open_source", "is_stream", "source_label",
]
