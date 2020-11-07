import asyncio
import random
from prompt_toolkit.application import Application, get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import VSplit, Window, HSplit, DynamicContainer
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import Checkbox, Frame, CheckboxList, Label
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.shortcuts import yes_no_dialog
from constants import PASSIVE_TYPES


class Gui:

    class CheckboxListNoScroll(CheckboxList):
        show_scrollbar = False

    def __init__(self, devices, states_queue, commands_queue):
        self.states_queue = states_queue
        self.commands_queue = commands_queue

        self._status = FormattedTextControl('')
        self._temperature_umidity = FormattedTextControl('')

        self._devices = self.gen_devices_dict(devices)

        self._passive_devices_dict = {
            id_: Window(FormattedTextControl(d.name))
            for id_, d in self._devices.items()
        }

        active, passive = self.get_devices_containers()

        self._active_devices_states = active
        self._passive_devices_states = passive

        self._is_running = True
        self._bindings = KeyBindings()

        @self._bindings.add('q')
        def _(event):
            self.stop()

        @self._bindings.add('c-p')
        def submit_command(_):
            selected_values = self._active_devices_states.current_values
            selected_values = [self._devices[id_] for id_ in selected_values]

            asyncio.gather(
                self.commands_queue.put(selected_values),
                self.show_status('States submitted!')
            )

    def stop(self):
        self._is_running = False
        asyncio.create_task(self.commands_queue.put(None))

        app = get_app()
        if app.is_running:
            app.exit()

    def get_devices_containers(self):
        active_devices_list = [
            [id_, d.name] for id_, d in self._devices.items()
            if d.type not in PASSIVE_TYPES
        ]
        active_devices = self.CheckboxListNoScroll(active_devices_list)

        passive_devices = [
            self._passive_devices_dict[id_] for id_, d in self._devices.items()
            if d.type in PASSIVE_TYPES
        ]
         
        return active_devices, passive_devices

    @staticmethod
    def gen_devices_dict(devices):
        return {(d.type, d.id): d for d in devices}

    def update_temperature_umidity(self, temperature, umidity):
        reference_temperature = '-'

        self._temperature_umidity.text = HTML(
            "\n<b>Environment:</b>\n\n"
            f"<i>Temperature:</i> {temperature}\n"
            f"<i>Umidity:</i> {umidity}\n"
            f"<i>Reference Temperature:</i> {reference_temperature}"
        )

    def update_devices_states(self, new_states):
        def get_name_str(id_):
            name = self._devices[id_].name
            color = 'green' if new_states[id_] else 'red'

            return HTML(f'<{color}>{name}</{color}>')

        for idx, (id_, _) in enumerate(self._active_devices_states.values):
            if id_ in new_states:
                self._active_devices_states.values[idx][1] = get_name_str(id_)

        for id_ in self._passive_devices_dict:
            if id_ in new_states:
                self._passive_devices_dict[id_].content.text = get_name_str(id_)

    async def update_states(self):
        def to_local_format(device_type, states):
            'To format usually used in this class'

            return {(device_type, idx): value
                    for idx, value in enumerate(reversed(states))}

        while self._is_running:
            new_states = await self.states_queue.get()
            device_type, devices_states, temperature, umidity = new_states

            devices_states = to_local_format(device_type, devices_states)

            self.update_devices_states(devices_states)
            self.update_temperature_umidity(temperature, umidity)

            get_app().invalidate()  # Refresh

    async def show_status(self, text):
        self._status.text = HTML(text)
        await asyncio.sleep(1)
        self._status.text = ''

    async def start(self):
        devices_states = VSplit(
            [
                HSplit([
                    Label(HTML("\n<b>Change states:</b>"), width=20),
                    HSplit([self._active_devices_states,]),

                    Label(HTML("\n<b>Passive devices:</b>"), width=20),
                    HSplit(self._passive_devices_states),

                    Label(HTML(
                        "<b>Device Colors:</b>\n\n"
                        "<i><green>Green:</green></i> turned on / detecting\n"
                        "<i><red>Red:</red></i> turned off / not detecting"
                    )),
                    
                ], padding=1),
                HSplit([
                    Window(self._temperature_umidity, width=30, height=9),
                    Label(HTML(
                        "<b>Commands:</b>\n\n"
                        '<i>ctrl+p:</i> Print state to system\n'
                        "<i>up/down:</i> Navigate\n"
                        "<i>space/enter:</i> Check boxes\n"
                        "<i>q:</i> Quit\n"
                    )),
                ], padding=1, padding_char=' ')
            ],
            padding_char=' ', padding=2
        )

        root_container = VSplit([Frame(
            title="Control Dashboard",
            body=HSplit([
                devices_states,
                Window(self._status, height=1, width=50, style='bg:#333333')
            ], padding=1)
        )], width=20, align="LEFT")

        layout = Layout(root_container)

        # Define application.
        application = Application(
            layout=layout,
            key_bindings=self._bindings,
            # refresh_interval=1,  # Controlling manually
            full_screen=True
        )

        await asyncio.gather(
            self.update_states(),
            application.run_async(),
        )
