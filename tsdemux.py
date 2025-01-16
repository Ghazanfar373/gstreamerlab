import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(None)

# Define the pipeline string (replace 'video_file_path' with the actual path to your video file)
video_file_path = "/home/serb/dayflight.mpg"  # Update this path
pipeline_string = f"""
filesrc location={video_file_path} ! tsparse ! tsdemux name=demux latency=0
demux. ! video/x-h264,alignment=au,stream-format=byte-stream ! queue ! h264parse ! avdec_h264 ! videoconvert ! textoverlay name=textoverlay text="Gstreamer" color=0x0000FF ! autovideosink sync=false
demux. ! meta/x-klv ! queue  ! appsink name=klv_sink sync=false
"""

# Create the pipeline
pipeline = Gst.parse_launch(pipeline_string)

# Get the appsink for KLV data
klv_sink = pipeline.get_by_name('klv_sink')

# Define a callback to process KLV data
def on_new_klv_sample(sink):
    sample = sink.emit('pull-sample')
    if sample:
        # Get the KLV buffer
        buffer = sample.get_buffer()
        # Extract data from the buffer
        klv_data = buffer.extract_dup(0, buffer.get_size())
        
        # Print or process the KLV data (for demonstration)
        print(f"KLV Data: {klv_data}")
        return Gst.FlowReturn.OK
    return Gst.FlowReturn.ERROR

# Connect the callback to the appsink's 'new-sample' signal
klv_sink.connect('new-sample', on_new_klv_sample)

# Start playing the pipeline
pipeline.set_state(Gst.State.PLAYING)

# Main loop to handle GStreamer bus messages (e.g., EOS, errors)
loop = GLib.MainLoop()

# Get the bus to check for events and handle messages
bus = pipeline.get_bus()

# Wait for the end of stream message or error
def bus_callback(bus, message):
    msg_type = message.type
    if msg_type == Gst.MessageType.EOS:
        print("End of Stream reached.")
        loop.quit()
    elif msg_type == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}, Debug Info: {debug}")
        loop.quit()

bus.add_signal_watch()
bus.connect("message", bus_callback)

# Run the main loop to keep the pipeline active
loop.run()

# Stop the pipeline once done
pipeline.set_state(Gst.State.NULL)


