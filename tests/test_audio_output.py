from services.audio_output import AudioOutput, find_airpods, find_headphones, find_speaker


def test_prefers_stereo_airpods_output_over_hands_free():
    outputs = [
        AudioOutput("hands-free", "Headset (AirPods Pro 3 Hands-Free)"),
        AudioOutput("stereo", "Headphones (AirPods Pro 3)"),
    ]

    assert find_airpods(outputs) == outputs[1]


def test_prefers_a_named_speaker_when_switching_back_from_airpods():
    outputs = [
        AudioOutput("monitor", "LG Monitor"),
        AudioOutput("realtek", "Speakers (Realtek(R) Audio)"),
        AudioOutput("airpods", "Headphones (AirPods Pro 3)"),
    ]

    assert find_speaker(outputs, exclude_id="airpods") == outputs[1]


def test_classifies_output_buttons_without_treating_airpods_as_headphones():
    airpods = AudioOutput("airpods", "Headphones (AirPods Pro 3)")
    headphones = AudioOutput("headphones", "WH-1000XM5 Headphones")
    speaker = AudioOutput("speaker", "Speakers (Realtek(R) Audio)")

    assert airpods.kind == "airpods"
    assert headphones.kind == "headphones"
    assert speaker.kind == "speaker"
    assert find_headphones([airpods, headphones]) == headphones
