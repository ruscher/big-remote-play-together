
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
try:
    gi.require_version('Vte', '3.91')
    from gi.repository import Vte
    print("Vte 3.91 loaded")
    import inspect
    print(dir(Vte.Terminal.spawn_async))
    print(Vte.Terminal.spawn_async.__doc__)
except Exception as e:
    print(e)
