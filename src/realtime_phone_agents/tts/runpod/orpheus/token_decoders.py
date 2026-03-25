from __future__ import annotations

import numpy as np
import torch
from snac import SNAC

_model = None
_snac_device = (
    "cuda"
    if torch.cuda.is_available()
    else "mps"
    if torch.backends.mps.is_available()
    else "cpu"
)


def _get_model():
    global _model
    if _model is None:
        _model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval()
        _model = _model.to(_snac_device)
    return _model


def convert_to_audio(multiframe, count):
    if len(multiframe) < 7:
        return None

    codes_0 = torch.tensor([], device=_snac_device, dtype=torch.int32)
    codes_1 = torch.tensor([], device=_snac_device, dtype=torch.int32)
    codes_2 = torch.tensor([], device=_snac_device, dtype=torch.int32)

    num_frames = len(multiframe) // 7
    frame = multiframe[: num_frames * 7]

    for j in range(num_frames):
        i = 7 * j

        if codes_0.shape[0] == 0:
            codes_0 = torch.tensor([frame[i]], device=_snac_device, dtype=torch.int32)
        else:
            codes_0 = torch.cat(
                [
                    codes_0,
                    torch.tensor([frame[i]], device=_snac_device, dtype=torch.int32),
                ]
            )

        if codes_1.shape[0] == 0:
            codes_1 = torch.tensor(
                [frame[i + 1]], device=_snac_device, dtype=torch.int32
            )
            codes_1 = torch.cat(
                [
                    codes_1,
                    torch.tensor(
                        [frame[i + 4]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
        else:
            codes_1 = torch.cat(
                [
                    codes_1,
                    torch.tensor(
                        [frame[i + 1]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
            codes_1 = torch.cat(
                [
                    codes_1,
                    torch.tensor(
                        [frame[i + 4]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )

        if codes_2.shape[0] == 0:
            codes_2 = torch.tensor(
                [frame[i + 2]], device=_snac_device, dtype=torch.int32
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 3]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 5]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 6]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
        else:
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 2]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 3]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 5]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 6]], device=_snac_device, dtype=torch.int32
                    ),
                ]
            )

    codes = [codes_0.unsqueeze(0), codes_1.unsqueeze(0), codes_2.unsqueeze(0)]
    if (
        torch.any(codes[0] < 0)
        or torch.any(codes[0] > 4096)
        or torch.any(codes[1] < 0)
        or torch.any(codes[1] > 4096)
        or torch.any(codes[2] < 0)
        or torch.any(codes[2] > 4096)
    ):
        return None

    with torch.inference_mode():
        audio_hat = _get_model().decode(codes)

    audio_slice = audio_hat[:, :, 2048:4096]
    audio_np = audio_slice.detach().cpu().numpy()
    audio_int16 = (audio_np * 32767).astype(np.int16)
    return audio_int16.tobytes()
