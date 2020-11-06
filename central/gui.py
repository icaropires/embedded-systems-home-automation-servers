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



class Gui:

    class CheckboxListNoScroll(CheckboxList):
        show_scrollbar = False

    def __init__(self, devices, states_queue, commands_queue):
        self.states_queue = states_queue
        self.commands_queue = commands_queue

        self._devices_names = dict(devices)

        self._temperature_umidity = FormattedTextControl('')
        self._devices_states = self.CheckboxListNoScroll(devices)
        self._status = FormattedTextControl('')

        self.bindings = KeyBindings()

        @self.bindings.add('q')
        def exit_(event):
            event.app.exit()

        @self.bindings.add('c-p')
        def submit_command(_):
            selected_values = self._devices_states.current_values

            asyncio.gather(
                self.commands_queue.put(selected_values),
                self.show_status('States submitted!')
            )

    async def show_status(self, text):
        self._status.text = HTML(text)
        await asyncio.sleep(1)
        self._status.text = ''

    def update_temperature_umidity(self):
        temperature = float(random.randint(0, 50))
        umidity = float(random.randint(0, 100))
        reference_temperature = '-'

        self._temperature_umidity.text = HTML(
            "\n<b>Environment:</b>\n\n"
            f"<i>Temperature:</i> {temperature}\n"
            f"<i>Umidity:</i> {umidity}\n"
            f"<i>Reference Temperature:</i> {reference_temperature}"
        )

    def update_devices_states(self):
        for i, (id_, _) in enumerate(self._devices_states.values):
            name = self._devices_names[id_]
            color = random.choice(('red', 'green'))
            self._devices_states.values[i][1] = HTML(f'<{color}>{name}</{color}>')

    async def update_states(self):
        while True:
            self.update_devices_states()
            self.update_temperature_umidity()

            await asyncio.sleep(1)

    async def start(self):
        devices_states = VSplit(
            [
                HSplit([
                    Label(HTML("\n<b>Choose the actives:</b>"), width=20),
                    VSplit([self._devices_states]),
                    Label(
                        HTML(
                            "<b>Device Colors</b>\n"
                            "    <i><green>Green:</green></i> active\n"
                            "    <i><red>Red:</red></i> inactive"
                        )
                    ),
                    
                ], padding=1),
                Window(self._temperature_umidity, width=30),
            ],
            padding_char=' ', padding=3
        )

        root_container = VSplit([Frame(  # I know, not pretty
            title="Control Dashboard",
            body=HSplit([
                devices_states,
                Window(self._status, height=1, width=50, style='bg:#222222')
            ], padding=1)
        )], width=20, align="LEFT")

        layout = Layout(root_container)

        # Define application.
        application = Application(
            layout=layout,
            key_bindings=self.bindings,
            refresh_interval=1,
            full_screen=True
        )

        await asyncio.gather(
            self.update_states(),
            application.run_async(),
        )

if __name__ == '__main__':
    devices = [
        [(1, 3), 'dev1'],
        [(2, 4), 'dev2'],
        [(3, 10), 'dev3'],
    ]
    gui = Gui(devices, asyncio.Queue(), asyncio.Queue())

    asyncio.run(gui.start())
