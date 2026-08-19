export type SceneStep =
  | "missionType"
  | "payloadSelection"
  | "roi"
  | "missionParameters"
  | "results";

export type MissionFamily = "remote_sensing" | "iot_communication" | "navigation" | null;

export type PayloadType =
  | "hyperspectral"
  | "multispectral"
  | "vhr_optical"
  | "thermal"
  | "sar"
  | "my_payload"
  | "ais"
  | "adsb"
  | "broadband"
  | "sigint"
  | "store_and_forward"
  | null;

export type RegionSelection =
  | {
      id: string;
      name: string;
      lat?: number;
      lon?: number;
    }
  | null;

export type ScenePose = {
  cameraPosition: [number, number, number];
  cameraTarget: [number, number, number];
  earthPosition: [number, number, number];
  earthScale: number;
  satellitePosition: [number, number, number];
  satelliteRotation: [number, number, number];
  satelliteVisible: boolean;
};
