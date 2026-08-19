import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import MissionFamilyPage from "./pages/MissionFamilyPage";
import PayloadPage from "./pages/PayloadPage";
import RoiPage from "./pages/RoiPage";
import ParametersPage from "./pages/ParametersPage";
import ResultPage from "./pages/ResultPage";
import AnalysisPage from "./pages/AnalysisPage";
import HelpPage from "./pages/HelpPage";
import ContactPage from "./pages/ContactPage";
import SceneCanvas from "./scene/SceneCanvas";
import RouteTransition from "./ui/RouteTransition";
import TopNav from "./ui/TopNav";

function RootLayout() {
  return (
    <div className="appRoot">
      <SceneCanvas />
      <div className="uiLayer">
        <TopNav />
        <RouteTransition>
          <Outlet />
        </RouteTransition>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<RootLayout />}>
        <Route path="/" element={<MissionFamilyPage />} />
        <Route path="/payload" element={<PayloadPage />} />
        <Route path="/roi" element={<RoiPage />} />
        <Route path="/parameters" element={<ParametersPage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/solver-trace" element={<AnalysisPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
