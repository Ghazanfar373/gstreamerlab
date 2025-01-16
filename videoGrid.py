import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, GLib, Gdk
import os

class VideoWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="2x2 Video Grid")
        
        # Get screen dimensions
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        # Calculate window size (80% of screen size)
        self.window_width = int(geometry.width * 0.8)
        self.window_height = int(geometry.height * 0.8)
        self.set_default_size(self.window_width, self.window_height)
        
        # Create main container with padding
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        #main_container.set_margin_start(2)
        #main_container.set_margin_end(2)
        #main_container.set_margin_top(2)
        #main_container.set_margin_bottom(2)
        self.add(main_container)
        
        # Create grid layout
        self.grid = Gtk.Grid()
        #self.grid.set_row_homogeneous(True)     # Equal height rows
        #self.grid.set_column_homogeneous(True)  # Equal width columns
        #self.grid.set_row_spacing(1)
        #self.grid.set_column_spacing(1)
        main_container.pack_start(self.grid, True, True, 0)
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Create four pipelines
        self.pipelines = []
        self.create_grid_pipelines()
        
        # Connect window events
        self.connect("destroy", self.on_destroy)
        self.connect("configure-event", self.on_window_resize)
        
        self.show_all()

    def create_grid_pipelines(self):
        video_files = [
            '/home/serb/dayflight.mpg',
            '/home/serb/dayflight.mpg',
            '/home/serb/dayflight.mpg',
            '/home/serb/dayflight.mpg'
        ]
        
        # Calculate initial video size
        video_width = (self.window_width - 30) // 2  # Account for margins and spacing
        video_height = (self.window_height - 30) // 2
        
        for i, video_file in enumerate(video_files):
            row = i // 2
            col = i % 2
            
            # Create aspect frame to maintain video aspect ratio
            aspect_frame = Gtk.AspectFrame(label=None, xalign=0.0, yalign=0.0, 
                                         ratio=16.0/9.0, obey_child=False)
            
            # Create GStreamer pipeline
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
                pipeline = Gst.parse_launch(pipeline_str)
                sink = pipeline.get_by_name('sink')
                
                # Get the widget from sink and add it to aspect frame
                sink_widget = sink.get_property('widget')
                aspect_frame.add(sink_widget)
                
                # Add aspect frame to grid
                self.grid.attach(aspect_frame, col, row, 1, 1)
                
                # Set up bus messages
                bus = pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect('message', self.on_message)
                
                self.pipelines.append(pipeline)
                
            except GLib.Error as e:
                print(f"Error creating pipeline: {e}")

        # Start playing with a small delay
        GLib.timeout_add(500, self.delayed_play)

    def on_window_resize(self, widget, event):
        # Update window dimensions
        self.window_width = event.width
        self.window_height = event.height
        return False

    def delayed_play(self):
        for pipeline in self.pipelines:
            pipeline.set_state(Gst.State.PLAYING)
        return False

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            pipeline = message.src.get_parent()
            pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
        elif t == Gst.MessageType.EOS:
            pipeline = message.src.get_parent()
            pipeline.set_state(Gst.State.NULL)
            print("End of stream")

    def on_destroy(self, widget):
        for pipeline in self.pipelines:
            pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

# Run the application
if __name__ == '__main__':
    window = VideoWindow()
    Gtk.main()