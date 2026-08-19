import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const OUT = path.dirname(fileURLToPath(import.meta.url));
const W = 1600;
const H = 900;
const C = {
  ink: "#15243A", muted: "#52657B", line: "#B8C5D3", pale: "#F4F7FA",
  blue: "#1769AA", bluePale: "#E8F2FA", teal: "#008A83", tealPale: "#E6F5F3",
  orange: "#D97706", orangePale: "#FFF3DF", violet: "#6D4CC3", violetPale: "#F0ECFA",
  red: "#B84646", white: "#FFFFFF",
};

const esc = (s) => String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

function base(title, subtitle) {
  return [`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`,
    `<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="${C.muted}"/></marker><filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#15304A" flood-opacity="0.10"/></filter></defs>`,
    `<rect width="1600" height="900" fill="${C.white}"/>`,
    text(72, 70, title, 34, C.ink, 700), text(72, 108, subtitle, 18, C.muted, 400),
    `<line x1="72" y1="132" x2="1528" y2="132" stroke="${C.line}"/>`];
}

function text(x, y, s, size=18, fill=C.ink, weight=400, anchor="start") {
  return `<text x="${x}" y="${y}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(s)}</text>`;
}

function multiline(x, y, lines, size=17, fill=C.muted, weight=400, line=27, anchor="start") {
  return `<text x="${x}" y="${y}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${lines.map((s,i)=>`<tspan x="${x}" dy="${i ? line : 0}">${esc(s)}</tspan>`).join("")}</text>`;
}

function box(x,y,w,h,title,lines=[],fill=C.white,stroke=C.line,accent=null) {
  const a = accent ? `<rect x="${x}" y="${y}" width="7" height="${h}" rx="3.5" fill="${accent}"/>` : "";
  return `<g filter="url(#shadow)"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>${a}</g>`+
    text(x+24,y+37,title,19,C.ink,700)+multiline(x+24,y+70,lines,15,C.muted,400,24);
}

function pill(x,y,w,label,fill,ink) {
  return `<rect x="${x}" y="${y}" width="${w}" height="34" rx="17" fill="${fill}"/>${text(x+w/2,y+23,label,14,ink,600,"middle")}`;
}

function arrow(x1,y1,x2,y2,label="", dashed=false) {
  const dash = dashed ? ` stroke-dasharray="8 7"` : "";
  const l = label ? `${text((x1+x2)/2,(y1+y2)/2-10,label,13,C.muted,600,"middle")}` : "";
  return `<path d="M${x1} ${y1} L${x2} ${y2}" stroke="${C.muted}" stroke-width="2" fill="none" marker-end="url(#arrow)"${dash}/>${l}`;
}

function save(name, body) {
  fs.writeFileSync(path.join(OUT, name), body.join("")+"</svg>\n", "utf8");
}

// Figure 1: deployed system architecture.
{
  const s = base("CubeSat Mission Configurator — System Architecture", "Separation of the immersive user interface, engineering services, optimization model, and data sources");
  s.push(
    pill(72,158,205,"PRESENTATION LAYER",C.bluePale,C.blue),
    box(72,205,300,170,"React / TypeScript UI",["Route-based mission wizard","Persistent WebGL scene","Results and analysis views"],C.white,C.line,C.blue),
    box(416,205,300,170,"Mission State",["Family and payload","ROI and revisit target","Engineering preferences"],C.white,C.line,C.blue),
    box(760,205,300,170,"API Client",["Validated JSON request","POST /mission/solve","Report request"],C.white,C.line,C.blue),
    arrow(372,290,416,290), arrow(716,290,760,290),
    pill(72,428,205,"ENGINEERING LAYER",C.tealPale,C.teal),
    box(72,475,235,180,"FastAPI Boundary",["Pydantic schemas","Input validation","Response assembly"],C.white,C.line,C.teal),
    box(343,475,235,180,"Requirement Engine",["Payload normalization","Requirement derivation","Bus candidate sizing"],C.white,C.line,C.teal),
    box(614,475,235,180,"Mission Analysis",["Orbit / constellation","Radiation screening","Warnings and trace"],C.white,C.line,C.teal),
    box(885,475,235,180,"CP-SAT Optimizer",["Discrete selections","Hard constraints","Multi-criteria objective"],C.white,C.line,C.orange),
    box(1156,475,372,180,"Design Output",["Selected bus and subsystems","Mass, power, cost and margins","PDF / Markdown mission report"],C.white,C.line,C.violet),
    arrow(910,375,190,475,"HTTP / JSON"), arrow(307,565,343,565), arrow(578,565,614,565), arrow(849,565,885,565), arrow(1120,565,1156,565),
    pill(72,710,172,"DATA SOURCES",C.orangePale,C.orange),
    box(270,700,320,120,"Payload Knowledge Base",["Remote sensing · IoT / comms","Navigation · compatibility rules"],C.pale,C.line,C.orange),
    box(640,700,320,120,"Engineering Libraries",["Bus, EPS, ADCS, COMMS, OBC","Thermal and propulsion tiers"],C.pale,C.line,C.orange),
    box(1010,700,320,120,"Global Assumptions",["Margins, efficiencies, scaling","Cost, risk and model constants"],C.pale,C.line,C.orange),
    arrow(430,700,460,655,"catalog data",true), arrow(800,700,995,655,"capacities",true), arrow(1170,700,1035,655,"coefficients",true),
    text(1528,862,"Figure 1",14,C.muted,600,"end")
  );
  save("figure_01_system_architecture.svg",s);
}

// Figure 2: end-to-end workflow and traceability.
{
  const s = base("Mission-to-Architecture Workflow", "The configurator converts user intent into a traceable preliminary CubeSat design through eight stages");
  const stages = [
    ["1","Mission family",["Remote sensing","IoT / communication","Navigation"],C.blue,C.bluePale],
    ["2","Payload definition",["Catalog payload","or confidential","‘My Payload’"],C.blue,C.bluePale],
    ["3","Mission context",["Region of interest","Revisit target","Preferences"],C.blue,C.bluePale],
    ["4","Requirements",["Volume and mass","Power and data","Pointing / thermal"],C.teal,C.tealPale],
    ["5","Mission analysis",["Orbit family","Constellation size","Bus candidates"],C.teal,C.tealPale],
    ["6","Optimization",["Bus + subsystem","CP-SAT feasibility","Cost / mass / risk"],C.orange,C.orangePale],
    ["7","Screening",["Margins","Radiation flags","Warnings"],C.orange,C.orangePale],
    ["8","Design result",["Architecture","Engineering trace","Mission report"],C.violet,C.violetPale],
  ];
  const pos=[[72,225],[450,225],[828,225],[1206,225],[1206,505],[828,505],[450,505],[72,505]];
  stages.forEach((st,i)=>{
    const [x,y]=pos[i], w=300;
    const category=i<3?["USER INPUT",C.bluePale,C.blue]:i<7?["COMPUTATION",C.tealPale,C.teal]:["OUTPUT",C.violetPale,C.violet];
    s.push(`<circle cx="${x+25}" cy="${y-25}" r="25" fill="${st[3]}"/>`,text(x+25,y-18,st[0],18,C.white,700,"middle"),
      box(x,y,w,190,st[1],st[2],st[4],st[3],st[3]),pill(x+170,y+140,110,category[0],category[1],category[2]));
  });
  s.push(arrow(372,320,440,320),arrow(750,320,818,320),arrow(1128,320,1196,320),
    `<path d="M1356 415 L1356 485" stroke="${C.muted}" stroke-width="2" fill="none" marker-end="url(#arrow)"/>`,
    arrow(1206,600,1138,600),arrow(828,600,760,600),arrow(450,600,382,600));
  s.push(
    `<rect x="72" y="745" width="1456" height="82" rx="16" fill="${C.pale}" stroke="${C.line}"/>`,
    text(100,778,"Traceability",18,C.ink,700),
    text(100,807,"Derived requirements, selections, margins and warnings are retained in the response trace.",16,C.muted,400),
    arrow(230,745,230,705,"trace returned with result",true),
    text(1528,862,"Figure 2",14,C.muted,600,"end")
  );
  save("figure_02_mission_workflow.svg",s);
}

// Figure 3: optimization formulation.
{
  const s = base("CP-SAT Subsystem Selection Model", "Finite-domain optimization with discrete design variables, coupled engineering constraints, and explainable outputs");
  s.push(
    pill(72,158,102,"INPUTS",C.bluePale,C.blue),
    box(72,205,300,150,"Mission requirements",["Payload mass, volume and power","Data, pointing and thermal needs","Orbit and user preferences"],C.white,C.line,C.blue),
    box(72,385,300,150,"Engineering data",["Bus capacity library","Subsystem tier libraries","Compatibility and assumptions"],C.white,C.line,C.blue),
    box(72,565,300,150,"Model parameters",["Margins and efficiencies","Integer scaling coefficients","Cost and risk weights"],C.white,C.line,C.blue),
    arrow(372,280,455,280),arrow(372,460,455,460),arrow(372,640,455,640),
    `<rect x="455" y="175" width="710" height="590" rx="20" fill="${C.pale}" stroke="${C.teal}" stroke-width="2.5"/>`,
    text(490,220,"OR-Tools CP-SAT model",25,C.ink,700),
    box(490,250,300,175,"Decision variables",["One bus class:  bᵤ ∈ {0,1}","One tier per subsystem:  yₛ,ₖ","EPS · ADCS · COMMS · OBC","THERMAL · PROPULSION"],C.white,C.line,C.teal),
    box(830,250,300,175,"Selection constraints",["Σ bᵤ = 1","Σ yₛ,ₖ = 1 for each subsystem","Tier compatibility masks","Bus-range compatibility"],C.white,C.line,C.teal),
    box(490,465,300,230,"Coupled hard constraints",["Volume  Utotal ≤ Uusable","Mass  Mtotal ≤ Mdry,max","Average and peak power closure","Storage and downlink capacity","Pointing, thermal and propulsion","Battery / solar / radiator limits"],C.white,C.line,C.orange),
    box(830,465,300,230,"Optimization objective",["Weighted, integer-scaled score","Minimize cost, mass and risk","Penalize excess capability","Respect user optimization priority","Return infeasible status if no","combination satisfies all constraints"],C.white,C.line,C.orange),
    arrow(790,337,830,337),arrow(640,425,640,465),arrow(980,425,980,465),
    arrow(1165,470,1245,470),
    pill(1245,158,117,"OUTPUTS",C.violetPale,C.violet),
    box(1245,205,283,150,"Selected architecture",["Bus class","Subsystem tiers","Optional components"],C.white,C.line,C.violet),
    box(1245,385,283,150,"Budget closure",["Total mass and power","Indicative cost","Residual margins"],C.white,C.line,C.violet),
    box(1245,565,283,150,"Engineering evidence",["Feasibility status","Warnings","Solver trace"],C.white,C.line,C.violet),
    arrow(1165,300,1245,280),arrow(1165,520,1245,460),arrow(1165,640,1245,640),
    `<rect x="455" y="800" width="710" height="42" rx="21" fill="${C.tealPale}"/>`,
    text(810,827,"Hard feasibility first; preference-based ranking second",16,C.teal,700,"middle"),
    text(1528,862,"Figure 3",14,C.muted,600,"end")
  );
  save("figure_03_cpsat_model.svg",s);
}

console.log("Generated 3 SVG thesis figures in", OUT);
