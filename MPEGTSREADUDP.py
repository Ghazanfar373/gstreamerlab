import gi
gi.require_version('Gst', '1.0')
import time
import os
from gi.repository import Gst, GObject, GLib
# Set XDG_RUNTIME_DIR environment variable
os.environ["XDG_RUNTIME_DIR"] = "/run/user/$(id -u)"
# Initialize GStreamer
Gst.init(None)
video_file_path = "/home/serb/dayflight.mpg"  # Replace with your video file path
# Define the pipeline
pipeline = Gst.parse_launch(f"""
    filesrc location={video_file_path}  ! tsparse ! tsdemux name=demux latency=0
    demux. ! video/x-h264,alignment=au,stream-format=byte-stream  ! queue ! h264parse ! avdec_h264 ! videoconvert ! textoverlay name=textoverlay text="Gstreamer" color=0x0000FF ! autovideosink sync=false
    demux. ! meta/x-klv ! queue  ! appsink name=klv_sink sync=false
""")
print("pipeline created ....")

# Get elements
klv_sink = pipeline.get_by_name("klv_sink")
textoverlay = pipeline.get_by_name("textoverlay")

# Dictionary to hold the latest KLV data based on its PTS
latest_klv_data = {}

# Set up a probe to intercept KLV data buffers on the klv_sink element
def klv_data_probe(pad, info):
    buffer = info.get_buffer()
    if buffer:
        klv_pts = buffer.pts
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if success:
            # Extract the KLV data and store it in a dictionary with the PTS as the key
            klv_data = map_info.data.decode('utf-8', errors='ignore')
            latest_klv_data[klv_pts] =  klv_data
            buffer.unmap(map_info)
            #print(klv_data)
        else:
            print("Failed to map buffer for KLV data extraction.")
    return Gst.PadProbeReturn.OK

# Attach the probe to the sink pad of the klv_sink
klv_sink_pad = klv_sink.get_static_pad("sink")
klv_sink_pad.add_probe(Gst.PadProbeType.BUFFER, klv_data_probe)

# Set up a probe to intercept video frames and apply KLV data and PTS overlay
def video_frame_probe(pad, info):
    buffer = info.get_buffer()
    if buffer:
        # Extract PTS of the video frame
        video_pts = buffer.pts

        # Find the closest KLV data PTS for overlay
        closest_klv_pts = max((pts for pts in latest_klv_data if pts <= video_pts), default=None)
        
        # Prepare overlay text with video PTS, KLV PTS, and KLV data
        overlay_text = f"Video PTS: {video_pts}"
        if closest_klv_pts is not None:
            klv_text = latest_klv_data[closest_klv_pts]
            overlay_text += f"\nKLV PTS: {closest_klv_pts}\nKLV Data: {klv_text}"
            
        else:
            overlay_text += "\nKLV PTS: None\nKLV Data: None"
        
        # Update the overlay text
        textoverlay.set_property("text", overlay_text)
        print(overlay_text)
        
    return Gst.PadProbeReturn.OK

# Add probe to the autovideosink's sink pad to overlay KLV data and PTS on each frame
video_sink = pipeline.get_by_name("autovideosink0")
if video_sink:
    video_sink_pad = video_sink.get_static_pad("sink")
    if video_sink_pad:
        video_sink_pad.add_probe(Gst.PadProbeType.BUFFER, video_frame_probe)

# Start the pipeline
pipeline.set_state(Gst.State.PLAYING)

# Run the main loop
loop = GLib.MainLoop()

# Set up a bus to listen for error messages
bus = pipeline.get_bus()
bus.add_signal_watch()

def on_message(bus, message):
    #print(f"Received message: {message.type}")
    if message.type == Gst.MessageType.EOS:
        print("End-of-Stream reached")
    #elif message.type == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}, {debug}")
    return True


bus.connect("message", on_message)

try:
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    # Stop the pipeline on exit
    pipeline.set_state(Gst.State.NULL)
