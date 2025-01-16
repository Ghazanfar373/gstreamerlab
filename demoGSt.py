import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, GLib
import os

class VideoWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Single Video Player")
        
        # Set window size
        self.set_default_size(800, 600)
        
        # Create a drawing area for the video
        self.video_area = Gtk.DrawingArea()
        self.add(self.video_area)
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Create the pipeline
        self.create_pipeline()
        
        self.connect("destroy", self.on_destroy)
        self.show_all()

    def create_pipeline(self):
        video_file = '/home/serb/dayflight.mpg'  # Replace with your video path
        
        # Create GStreamer pipeline with gtksink and queue
        pipeline_str = (
            f'filesrc location="{video_file}" ! '
            'queue max-size-buffers=4096 max-size-bytes=0 max-size-time=0 ! '
            'decodebin ! '
            'queue ! '
            'videoconvert ! '
            'videoscale ! '
            'video/x-raw,format=BGRA ! '
            'queue ! '
            'gtksink name=sink sync=true'
        )
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            sink = self.pipeline.get_by_name('sink')
            
            # Get the widget from sink and add it to our window
            sink_widget = sink.get_property('widget')
            self.remove(self.video_area)  # Remove the drawing area
            self.add(sink_widget)  # Add the sink widget directly
            
            # Set up bus messages
            bus = self.pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect('message', self.on_message)
            
            # Start playing with a small delay
            GLib.timeout_add(500, self.delayed_play)
            
        except GLib.Error as e:
            print(f"Error creating pipeline: {e}")

    def delayed_play(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        return False  # Don't repeat the timeout

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
        elif t == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            print("End of stream")

    def on_destroy(self, widget):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

# Run the application
if __name__ == '__main__':
    window = VideoWindow()
    Gtk.main()