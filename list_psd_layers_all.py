from psd_tools import PSDImage

def print_layers(layers, prefix=""):
    for layer in layers:
        print(f"{prefix}- {layer.name} | {layer.kind}")
        # 遞迴列出所有子圖層，支援多種 psd-tools 版本
        group_layers = None
        if hasattr(layer, 'is_group') and callable(layer.is_group) and layer.is_group():
            if hasattr(layer, 'layers'):
                group_layers = layer.layers
            elif hasattr(layer, 'children'):
                group_layers = layer.children
        elif hasattr(layer, 'layers') and len(layer.layers) > 0:
            group_layers = layer.layers
        elif hasattr(layer, 'children') and len(layer.children) > 0:
            group_layers = layer.children
        if group_layers is not None:
            print_layers(group_layers, prefix + "  ")

if __name__ == "__main__":
    psd_path = "晚報YT縮圖.psd"
    try:
        psd = PSDImage.open(psd_path)
        print(f"PSD: {psd_path}")
        print_layers(psd, "")
    except Exception as e:
        print(f"讀取 PSD 失敗: {e}")
