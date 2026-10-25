import * as ImagePicker from "expo-image-picker";
import { Platform } from "react-native";

export type PickedPhoto = { status: "ok"; base64: string; uri: string } | { status: "cancelled" } | { status: "denied"; blocked: boolean } | { status: "failed" };

// Take a photo with the camera (on the web, the file picker, with the camera on a phone browser) or choose one from the library.
// The photo is compressed and returned as base64; nothing is stored.
export async function pickPhoto(kind: "camera" | "library" = "camera"): Promise<PickedPhoto> {
  if (Platform.OS !== "web") {
    const current = kind === "camera" ? await ImagePicker.getCameraPermissionsAsync() : await ImagePicker.getMediaLibraryPermissionsAsync();
    let granted = current.status === "granted";
    let canAsk = current.canAskAgain;
    if (!granted && canAsk) {
      const requested = kind === "camera" ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
      granted = requested.status === "granted";
      canAsk = requested.canAskAgain;
    }
    if (!granted) return { status: "denied", blocked: !canAsk };
  }
  try {
    const options: ImagePicker.ImagePickerOptions = { base64: true, quality: 0.4, mediaTypes: ["images"] };
    const picked = kind === "camera" ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    const asset = picked.assets?.[0];
    if (picked.canceled || !asset?.base64) return { status: "cancelled" };
    return { status: "ok", base64: asset.base64, uri: asset.uri };
  } catch {
    return { status: "failed" };
  }
}
