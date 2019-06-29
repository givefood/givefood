from django.dispatch import Signal

# Signals will only be fired when using GAE modules, not when autoscaling
module_started = Signal(providing_args=['request'])
module_stopped = Signal(providing_args=['request'])

