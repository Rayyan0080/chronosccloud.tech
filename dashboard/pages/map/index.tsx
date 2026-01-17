import OttawaCesiumMap from '../../components/OttawaCesiumMap';

export default function Map() {
  return (
    <div className="w-full" style={{ height: 'calc(100vh - 200px)' }}>
      <div className="mb-4">
        <h1 className="text-4xl font-bold text-white mb-2">3D Map - Ottawa Region</h1>
        <p className="text-gray-400">Interactive 3D visualization with geospatial overlays</p>
      </div>
      
      <div className="w-full h-full rounded-lg overflow-hidden border border-dark-border">
        <OttawaCesiumMap />
      </div>
    </div>
  );
}
