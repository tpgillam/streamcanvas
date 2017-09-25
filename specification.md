Specification (from Chris)
==========================


1. StreamCanvas takes input from stdin.

2. Any controls affecting StreamCanvas start-up that are available through command line args must also be settable via
   the input stream, so that control can be (if neecessary) exclusively in-stream.

3. Whatever else happens, StreamCanvas must exert minimal back-pressure on running commands. Whereas hist needed to
   absorb “all” events, and either plot them or store them, the StreamCanvas has a concept of “frames”, and is permitted
   to drop frames (unless explicitely told not to do so).  It should therefore be able to absorb frames fast, (if
       necessary via having an independent thread that absorbs frames very quickly with no back pressure), and discard
   those it does not need.  Unless told not to do so, under most circumstances StreamCanvas may legitimately retain, in
   memory:  (a) the currently displayed frame, (b) the most-recent complete frame (available for drawing on request),
   (c) the (incomplete) frame that is arriving on the input stream.

4. A Frame is described on the input stream, and consists of a collection of 2D or 3D drawable objects and meta-commands
   (eg co-ord system transforms, viewport rotations, line-thickness settings, etc).  It shall be clear where a frame
   starts and ends … e.g. “end of frame” was signified in my old StreamCanvas by the reserved word “approve”.  2D
   objects by default appear with Z=0, and default implementation should make them appear as-if 3rd dim was not present.

5. It should be possible to both (a) progressively draw incomplete frames step-wise on the canvas (e.g. in the manner
   that a web-page can begin to be displayed to the user prior to the full loading of its content) and (b) draw complete
frames into a double buffer for a buffer fast switch.

6. Stream has “live” and “inspection” modes.  “inspection” comes in “dropping” (default) and “non-dropping” (selectable)
  variants.

    1. “inspection mode”:  In this mode, the first frame to appear on the input stream is progressively drawn until it
       is complete.  Other frames may continue to arrive on the input stream, but are not shown until specifically
       requested to be shown by the user.  The user indicates such a desire by (say) pressing “n” for “next frame”, or
       clicking a “next” button in the gui.  If “n” is pressed, then in  “dropping” mode the MOST RECENT COMPLETE FRAME
       ON THE INPUT STREAM is displayed.  [Ideally it has already been drawn into a double buffer, and is simply blatted
       into view instantly.  The definition of MOST RECENT is flexlibe, in that it may mean “THE MOST RECENTLY FRAME
       AVAILABLE IN THE DOUBLE BUFFER”, for example.]  Such display should ideally be instantaneous rather than
       progressive, UNLESS there has been only one full and one incomplete frame on the input stream.  In the latter
       case, progressive display is permitted.  If there is no new frame extending beyond the most recently drawn
       buffer, the request for “n” should be rejected.  In “non-dropping” mode, instead the StreamCanvas promises not to
       drop frames, and if necessary buffers the entire input stream to memory, and so responds to “n” by drawing THE
       FRAME THAT WAS SENT AFTER THE ONE CURRENTLY DISPLAYED.  In non-dropping mode it should be possible for the user
       to interactively demand a “catch up” command that says, OK, now I want to catch up to the head of the frame
       buffer, you may now discard all frames between the one currently shown and the last complete one in the frame
       buffer.


    2. “live” mode is like dropping inspection mode, except the user is assumed to be pressing “n” all the time, and so
       sees a video-like display of the most recent compete frame.


7. The input stream spec is still up for grabs.  I have a current example (below) but there are things about it that
   were not good — hence desire for change.  Wait on further news for the specific input stream spec.

8. The gui allows the user to, live, zoom in or out to parts of the display, rotate/translate the viewed objects in 3D,
  turn on-or-off axes, etc.

9. 2D axes should by default be drawn, as in hist, but be turn-offable, or 3D able if necessary.

10. It should be possible for the user to assert that his stream will be entirely 2D to allow the Stream Canvas to
    reject 3D options and streams, and thereby run optimised for 2D in various ways.

11. The StreamCanvas should not demand prior knowledge of max/min view paramenters (c.f. “l” and “u” in hist) and should
    be intelligent enough to find an initial viewport or set of axes that is sensible, and that adapts to the stream as
    it grows, though the user should be able to override this with “l, lx, ux, u, ux, uy” specifications, etc.

12. If the widest buffer grows in width in autosizing mode, the autosized viewport should grow too, but the reverse it
    not true.  Smaller frames after wider ones should not (by default) cause reduction in viewport size.
