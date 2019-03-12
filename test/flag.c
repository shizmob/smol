/* "Tiny X11 Trans Flag" by Suricrasia Online, edited a bit to make testing
 * easier */
#include<X11/X.h>
#include<X11/Xlib.h>
#include<X11/Xutil.h>
#include <X11/Xatom.h>

#define CANVAS_WIDTH 400
#define CANVAS_HEIGHT ((CANVAS_WIDTH * 2)/3)

#define COLOR(r, g, b) ((r << 16) + (g << 8) + b)

__attribute__((__used__,__externally_visible__))
void _start() {
/*int main() {*/
#ifdef MAKE_ESC_WORK
  Atom wmDeleteMessage;
#endif

  //initialize the window
  Display* dpy = XOpenDisplay(NULL);

  //this is so the window isn't resizable
  static XSizeHints hints = {
    .flags = USPosition | PMinSize | PMaxSize,
    .width = CANVAS_WIDTH,     .height = CANVAS_HEIGHT,
    .max_width = CANVAS_WIDTH, .max_height = CANVAS_HEIGHT,
    .min_width = CANVAS_WIDTH, .min_height = CANVAS_HEIGHT,
  };

  //it seems like just keeping this as 0 is probs ok... lol
  const int s = 0;//DefaultScreen(dpy);
  Window win = XCreateSimpleWindow(dpy, RootWindow(dpy, s), 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, 0, 0, COLOR(89, 200, 243));

#ifdef MAKE_ESC_WORK
  wmDeleteMessage = XInternAtom(dpy, "WM_DELETE_WINDOW", False);
  XSetWMProtocols(dpy, win, &wmDeleteMessage, 1);
#endif

  XSelectInput(dpy, win, ExposureMask|KeyPressMask);
  XSetWMNormalHints(dpy, win, &hints);

  //this actually opens the window
  XMapWindow(dpy, win);

  XEvent xev;
  static XGCValues vals = {};
  while(1/*XPending(dpy)>0*/) {
    XNextEvent(dpy, &xev);
    if (xev.type == Expose) {
      GC gc = DefaultGC(dpy, s);
      vals.foreground = COLOR(237, 165, 179);
      XChangeGC(dpy, gc, GCForeground, &vals);
      XFillRectangle(dpy, win, gc, 0, CANVAS_HEIGHT/5, CANVAS_WIDTH, CANVAS_HEIGHT * 3/5);
      vals.foreground = COLOR(255, 255, 255);
      XChangeGC(dpy, gc, GCForeground, &vals);
      XFillRectangle(dpy, win, gc, 0, CANVAS_HEIGHT* 2/5, CANVAS_WIDTH, CANVAS_HEIGHT * 1/5);
    }
#ifdef MAKE_ESC_WORK
    else if (xev.type == KeyPress) {
        if (((XKeyPressedEvent*)&xev)->keycode == XKeysymToKeycode(dpy,XK_Escape)) _exit(0);
    } else if (xev.type == ClientMessage) {
        if (xev.xclient.data.l[0] == wmDeleteMessage) _exit(0);
    }
    // swap buffers here
#endif
  }
}

