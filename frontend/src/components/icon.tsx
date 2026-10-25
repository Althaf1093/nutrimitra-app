import type { LucideIcon } from "lucide-react-native";
import Activity from "lucide-react-native/icons/activity";
import Apple from "lucide-react-native/icons/apple";
import ArrowRight from "lucide-react-native/icons/arrow-right";
import ArrowUp from "lucide-react-native/icons/arrow-up";
import Bean from "lucide-react-native/icons/bean";
import Beer from "lucide-react-native/icons/beer";
import Bell from "lucide-react-native/icons/bell";
import Cake from "lucide-react-native/icons/cake";
import CalendarDays from "lucide-react-native/icons/calendar-days";
import Camera from "lucide-react-native/icons/camera";
import Carrot from "lucide-react-native/icons/carrot";
import ChartColumn from "lucide-react-native/icons/chart-column";
import Check from "lucide-react-native/icons/check";
import ChevronDown from "lucide-react-native/icons/chevron-down";
import ChevronLeft from "lucide-react-native/icons/chevron-left";
import ChevronRight from "lucide-react-native/icons/chevron-right";
import ChevronUp from "lucide-react-native/icons/chevron-up";
import CircleAlert from "lucide-react-native/icons/circle-alert";
import Circle from "lucide-react-native/icons/circle";
import CupSoda from "lucide-react-native/icons/cup-soda";
import Download from "lucide-react-native/icons/download";
import Droplet from "lucide-react-native/icons/droplet";
import Dumbbell from "lucide-react-native/icons/dumbbell";
import Egg from "lucide-react-native/icons/egg";
import Eye from "lucide-react-native/icons/eye";
import EyeOff from "lucide-react-native/icons/eye-off";
import Fish from "lucide-react-native/icons/fish";
import Flame from "lucide-react-native/icons/flame";
import Footprints from "lucide-react-native/icons/footprints";
import Globe from "lucide-react-native/icons/globe";
import Heart from "lucide-react-native/icons/heart";
import House from "lucide-react-native/icons/house";
import IceCreamCone from "lucide-react-native/icons/ice-cream-cone";
import Info from "lucide-react-native/icons/info";
import Leaf from "lucide-react-native/icons/leaf";
import Lock from "lucide-react-native/icons/lock";
import LogOut from "lucide-react-native/icons/log-out";
import Mail from "lucide-react-native/icons/mail";
import MessageCircle from "lucide-react-native/icons/message-circle";
import Mic from "lucide-react-native/icons/mic";
import Milk from "lucide-react-native/icons/milk";
import Minus from "lucide-react-native/icons/minus";
import Monitor from "lucide-react-native/icons/monitor";
import Moon from "lucide-react-native/icons/moon";
import Palette from "lucide-react-native/icons/palette";
import Pencil from "lucide-react-native/icons/pencil";
import Pizza from "lucide-react-native/icons/pizza";
import Plus from "lucide-react-native/icons/plus";
import RotateCw from "lucide-react-native/icons/rotate-cw";
import Salad from "lucide-react-native/icons/salad";
import ScanBarcode from "lucide-react-native/icons/scan-barcode";
import Search from "lucide-react-native/icons/search";
import Send from "lucide-react-native/icons/send";
import Settings from "lucide-react-native/icons/settings";
import Share2 from "lucide-react-native/icons/share-2";
import Shield from "lucide-react-native/icons/shield";
import ShoppingBasket from "lucide-react-native/icons/shopping-basket";
import Soup from "lucide-react-native/icons/soup";
import Sparkles from "lucide-react-native/icons/sparkles";
import Sun from "lucide-react-native/icons/sun";
import Sunrise from "lucide-react-native/icons/sunrise";
import Target from "lucide-react-native/icons/target";
import Trash from "lucide-react-native/icons/trash";
import TriangleAlert from "lucide-react-native/icons/triangle-alert";
import User from "lucide-react-native/icons/user";
import Utensils from "lucide-react-native/icons/utensils";
import Wheat from "lucide-react-native/icons/wheat";
import Wine from "lucide-react-native/icons/wine";
import WifiOff from "lucide-react-native/icons/wifi-off";
import X from "lucide-react-native/icons/x";
import { type ColorValue, View } from "react-native";

// One line-icon set (Lucide, ISC licence) for the whole app. Names are the semantic names the screens use; the older SF Symbol
// names the code base started with map to the same icons, so every place looks the same on iOS, Android and the web.
export const ICONS: Record<string, LucideIcon> = {
  // navigation
  today: House,
  plan: CalendarDays,
  coach: MessageCircle,
  progress: ChartColumn,
  insights: ChartColumn,
  kitchen: ShoppingBasket,
  settings: Settings,
  // actions
  add: Plus,
  remove: Minus,
  close: X,
  check: Check,
  back: ChevronLeft,
  next: ChevronRight,
  up: ChevronUp,
  down: ChevronDown,
  send: Send,
  arrowUp: ArrowUp,
  arrowRight: ArrowRight,
  refresh: RotateCw,
  camera: Camera,
  search: Search,
  edit: Pencil,
  trash: Trash,
  share: Share2,
  download: Download,
  mic: Mic,
  barcode: ScanBarcode,
  signOut: LogOut,
  // status
  info: Info,
  warning: TriangleAlert,
  alert: CircleAlert,
  offline: WifiOff,
  lock: Lock,
  shield: Shield,
  mail: Mail,
  eye: Eye,
  eyeOff: EyeOff,
  globe: Globe,
  user: User,
  bell: Bell,
  palette: Palette,
  monitor: Monitor,
  moon: Moon,
  sun: Sun,
  // wellness
  sparkles: Sparkles,
  leaf: Leaf,
  heart: Heart,
  flame: Flame,
  target: Target,
  water: Droplet,
  walk: Footprints,
  activity: Activity,
  strength: Dumbbell,
  // meals
  breakfast: Sunrise,
  lunch: Sun,
  snack: Apple,
  dinner: Moon,
  drinks: CupSoda,
  // food categories
  tiffin: Soup,
  rice: Wheat,
  dal: Bean,
  curry: Utensils,
  vegetables: Carrot,
  fruits: Apple,
  salad: Salad,
  egg: Egg,
  fish: Fish,
  dairy: Milk,
  sweets: Cake,
  icecream: IceCreamCone,
  pizza: Pizza,
  beer: Beer,
  wine: Wine,
  default: Circle,

  // SF Symbol names used by older call sites
  xmark: X,
  checkmark: Check,
  "chevron.right": ChevronRight,
  "arrow.clockwise": RotateCw,
  "arrow.up": ArrowUp,
  "camera.fill": Camera,
  "sun.max.fill": House,
  "list.bullet.clipboard": CalendarDays,
  "chart.line.uptrend.xyaxis": ChartColumn,
  "bubble.left.and.bubble.right.fill": MessageCircle,
  "leaf.fill": Leaf,
  "heart.text.square.fill": Heart,
  gearshape: Settings,
  "gearshape.fill": Settings,
  "figure.walk": Footprints,
  "sunrise.fill": Sunrise,
  "moon.stars.fill": Moon,
  "circle.grid.2x2.fill": Sun,
};

export type IconName = keyof typeof ICONS | (string & {});

// The testID keeps the old name so existing tests that look for `icon-<name>` keep working.
export function AppIcon({ name, color, size = 22, strokeWidth = 1.9 }: { name: IconName; color: ColorValue; size?: number; strokeWidth?: number }) {
  const Glyph = ICONS[name] ?? ICONS.default;
  return (
    <View testID={`icon-${name}`} accessibilityRole="image" style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Glyph color={color as string} size={size} strokeWidth={strokeWidth} />
    </View>
  );
}
