# Teenage Engineering OP-XY Drum Preset Utility

This script is a proof of concept designed to facilitate the creation and convertion (from OP-1 and OP-1 Field) of drum sampler patches for the Teenage Engineering OP-XY

## Features

1. **Convert OP-1 Drum Patches**:
   - Extracts individual samples from `.aif` drum patch files.
   - Generates a `.preset` folder containing the audio samples and metadata file (patch.json).

2. **Create New Presets**:
   - Creates a new OP-XY drum preset from a folder of `.wav` files.
   - Supports assigning samples to keys based on a standard OP-1 drum layout or a numerical ordering.

## Usage

```bash
python teopxy.py <convert|create> <path> [--layout=<standard|number>]
```

### Commands

- **convert**: Extracts samples and metadata from an existing `.aif` OP-1 drum patch.
- **create**: Creates a new drum preset from a folder of `.wav` files.

### Convert options

- `<path>`: The file path to the `.aif` file (for `convert`) or the folder containing `.wav` files (for `create`).


### Create options
- `<path>`: The path to a folder containing `.wav` files (for `create`). Also supports matching multiple folders using a wildcard.
- `--layout`(optional): Specifies how samples should be assigned to keys. Options:
  - `standard` (default): Assigns samples based on keywords in filenames to match the OP-1 drum layout.
  - `number`: Assigns samples based on numerical ordering or alphabetical sorting.
- `--output` (optional): The directory where presets will be saved. Defaults to the same directory as the source.
- `--gaps` (optional): When assigning samples based on keyword matching, leave gaps in order to strictly adhere to the desired key mapping. If set to false then the order of samples will be adhered to, but no gaps will be create so all samples will be on arranged sequential keys. Defaults to true. 

## Standard OP-1 Drum Layout

When using the `standard` layout, the script attempts to match `.wav` file names to the following key assignments:

| Key | Assignment         | Keywords                         |
|-----|--------------------|----------------------------------|
| 1   | Kick               | `kick`                          |
| 2   | Kick               | `kick`                          |
| 3   | Snare              | `snare`                         |
| 4   | Snare              | `snare`                         |
| 5   | Rimshot/Rim        | `rimshot`, `rim`                |
| 6   | Clap and Hand      | `clap`, `hand`                  |
| 7   | Tambourine/Shaker  | `tambourine`, `shaker`          |
| 9   | Closed Hi-Hat      | `hihat`, `hi-hat`, `closed`     |
| 11  | Open Hi-Hat        | `hihat`, `hi-hat`, `open`       |
| 14  | Ride Cymbal        | `ride`, `cymbal`                |
| 16  | Crash Cymbal       | `crash`, `cymbal`               |
| 20–24 | Bass              | `bass`, `synth`                          |

### Notes on File Matching

- Files are assigned to keys based on keywords in their names.
- Keywords containing multiple terms (e.g., `clap` and `hand`) will try to match all terms in the filename, but will settle on fewer.
- If multiple matches exist, files with the greatest number of keywords matched will be perferred.
- Any unused files are assigned to any remaining empty key slots.

## Example Commands

### Convert an OP-1 Drum Patch

```bash
python teopxy.py convert path/to/drum_patch.aif
```

This will extract individual samples from the `.aif` file and save them in a `.preset` folder.

### Create a New Preset

#### Using Standard Layout

```bash
python teopxy.py create path/to/samples --layout=standard
```

This will assign `.wav` files to keys based on the OP-1 drum layout.

#### Using Number Layout

```bash
python teopxy.py create "path/to/samples/*" --layout=number
```

This will process multiple directoryes under the samples directory, and will assign `.wav` files to keys numerically or alphabetically.

## Output

- For both commands, a folder named `<base_name>.preset` is created with the same name as the input directory.
- The directory contains:
  - Individual `.wav` files (for `convert`) or copies of input `.wav` files (for `create`).
  - A `patch.json` file containing metadata for the OP-1 drum preset.

## Requirements

- Python 3.6+
- `pydub` library
- `ffmpeg` or `libav` installed and configured

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/paul-sneddon/teopxy.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## License

This project is licensed under the GNU General Public License (GPL). For more details, see the LICENSE file or visit https://www.gnu.org/licenses/gpl-3.0.html.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

