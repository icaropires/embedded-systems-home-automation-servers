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



class Gui:

    bindings = KeyBindings()

    class CheckboxListNoScroll(CheckboxList):
        show_scrollbar = False

    def __init__(self):
        self.devices_names = {i: f'device{i}' for i in range(1, 11)}

        self.temperature_umidity = FormattedTextControl('')
        self.devices_states = self.CheckboxListNoScroll(
            [[i, self.devices_names[i]]
                for i in range(1, 11)]
        )

    @bindings.add('q')
    def exit_(event):
        event.app.exit()

    def update_temperature_umidity(self):
        temperature = float(random.randint(0, 50))
        umidity = float(random.randint(0, 100))
        reference_temperature = '-'

        self.temperature_umidity.text = HTML(
            "\n<b>Environment:</b>\n\n"
            f"<i>Temperature:</i> {temperature}\n"
            f"<i>Umidity:</i> {umidity}\n"
            f"<i>Reference Temperature:</i> {reference_temperature}"
        )

    def update_devices_states(self):
        for i, (id_, _) in enumerate(self.devices_states.values):
            name = self.devices_names[id_]
            color = random.choice(('red', 'green'))
            self.devices_states.values[i][1] = HTML(f'<{color}>{name}</{color}>')

    async def update_states(self):
        while True:
            self.update_devices_states()
            self.update_temperature_umidity()

            await asyncio.sleep(1)

    async def start(self):
        root_container = VSplit([Frame(  # I know, not pretty
            title="Control Dashboard",
            body=VSplit(
                [
                    HSplit([
                        Label(HTML("\n<b>Choose the actives:</b>"), width=20),
                        VSplit([self.devices_states]),
                        Label(
                            HTML(
                                "<b>Device Colors</b>\n"
                                "    <i>Green:</i> active\n"
                                "    <i>Red:</i> inactive"
                            )
                        ),
                    ], padding=1),
                    Window(self.temperature_umidity, width=30)
                ],
                padding_char=' ', padding=3
            )
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
    gui = Gui()
    asyncio.run(gui.start())
