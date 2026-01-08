# 列出 PSD 所有圖層結構與型態，協助定位 Rectangle 2
from psd_tools import PSDImage

def print_layers(layers, prefix=""):
    for layer in layers:
        print(f"{prefix}- {layer.name} | {layer.kind}")
        if hasattr(layer, 'layers') and len(layer.layers) > 0:
            print_layers(layer.layers, prefix + "  ")

if __name__ == "__main__":
    psd_path = "晚報YT縮圖.psd"
    try:
        psd = PSDImage.open(psd_path)
        print(f"PSD: {psd_path}")
        print_layers(psd, "")
    except Exception as e:
        print(f"讀取 PSD 失敗: {e}")
