# cambridge_851n
Custom component for Home Assistant that integrates with the Cambridge Audio
Azur 851N network media player.  This integration will add a new Media Player
entity to your Home Assistant installation.

Create a directory called `cambridge_851n` under the `custom_components`
directory, and save the files from this repo in there.

Enable the component by adding the following to `configuration.yaml`

```
media_player:
  - platform: cambridge_851n
    host: <ip or hostname>
    name: Cambridge Azur 851N
```
