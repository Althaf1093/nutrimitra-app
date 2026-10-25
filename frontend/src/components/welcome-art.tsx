import { View } from "react-native";
import Svg, { Circle, Ellipse, Path } from "react-native-svg";

import { makeStyles, radius } from "@/src/theme";

const useArt = makeStyles(() => ({
  frame: { borderRadius: radius.xl + 4, backgroundColor: "#3F6254", overflow: "hidden", alignItems: "center", justifyContent: "center", height: 250, width: "100%" },
}));

// An original illustration: a bowl of colourful food on a green field. The colours are fixed so it looks the same in light and dark.
export function WelcomeArt() {
  const styles = useArt();
  return (
    <View style={styles.frame} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Svg width={340} height={250} viewBox="0 0 340 250">
        <Circle cx={70} cy={60} r={90} fill="#4A6B5D" />
        <Circle cx={300} cy={220} r={110} fill="#365547" />
        <Ellipse cx={170} cy={168} rx={92} ry={22} fill="#24382F" opacity={0.35} />
        <Path d="M82 120h176a86 70 0 0 1-176 0z" fill="#FBF8F2" />
        <Path d="M82 120h176" stroke="#E4EEE8" strokeWidth={4} />
        <Circle cx={130} cy={108} r={22} fill="#F4B563" />
        <Circle cx={172} cy={100} r={26} fill="#8FD3C0" />
        <Circle cx={214} cy={108} r={22} fill="#F2A08F" />
        <Path d="M150 92c4-14 14-22 24-24 0 12-8 22-24 24z" fill="#E4EEE8" />
        <Path d="M196 90c6-12 16-18 28-18-2 12-12 20-28 18z" fill="#BDB1EA" />
      </Svg>
    </View>
  );
}
