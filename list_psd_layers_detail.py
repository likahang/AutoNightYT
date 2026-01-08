from psd_tools import PSDImage

def print_layers(layers, prefix=""):
    for layer in layers:
        print(f"{prefix}- {layer.name} | {layer.kind}")
        # debug: 顯示 children/layers 屬性
        if hasattr(layer, 'children'):
            print(f"{prefix}  [children] len={len(layer.children)} type={type(layer.children)}")
        if hasattr(layer, 'layers'):
            print(f"{prefix}  [layers] len={len(layer.layers)} type={type(layer.layers)}")
        # 遞迴列出
        if hasattr(layer, 'children') and len(layer.children) > 0:
            print_layers(layer.children, prefix + "  ")
        elif hasattr(layer, 'layers') and len(layer.layers) > 0:
            print_layers(layer.layers, prefix + "  ")

if __name__ == "__main__":
    psd_path = "晚報YT縮圖.psd"
    try:
        psd = PSDImage.open(psd_path)
        for layer in psd:
            if layer.name == "效果":
                print(f"效果 group:")
                group_layers = getattr(layer, 'children', getattr(layer, 'layers', []))
                print_layers(group_layers, "  ")
            if layer.name == "精華版_顏色可變":
                print(f"精華版_顏色可變 group:")
                group_layers = getattr(layer, 'children', getattr(layer, 'layers', []))
                print_layers(group_layers, "  ")
    except Exception as e:
        print(f"讀取 PSD 失敗: {e}")
