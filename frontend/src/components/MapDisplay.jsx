import React, { useEffect, useRef } from 'react';

const MapDisplay = ({ center, hospitals = [], onNavigate = () => {}, onMapLoaded = () => {} }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markers = useRef([]);

  useEffect(() => {
    // Dynamically load AMap script
    const loadScript = () => {
      const AMapKey = import.meta.env.VITE_AMAP_JS_API_KEY;
      console.log("AMap JS API Key:", AMapKey);

      if (window.AMap) {
        console.log("window.AMap已存在，直接初始化地图。");
        initMap();
        return;
      }
      const script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMapKey}&plugin=AMap.Driving,AMap.PlaceSearch,AMap.Transit,AMap.Walking`; // 根据官网示例添加全部导航插件
      script.async = true;
      script.onerror = () => {
        console.error("高德地图JS API加载失败，请检查网络或API Key。");
      };
      script.onload = () => {
        console.log("高德地图JS API脚本加载完成。");
        initMap();
      };
      document.head.appendChild(script);
    };

    const initMap = () => {
      console.log("尝试初始化地图...");
      if (!mapRef.current || !window.AMap) {
        console.log("地图容器或window.AMap未准备好，跳过初始化。");
        return;
      }
      
      mapInstance.current = new window.AMap.Map(mapRef.current, {
        center: center ? [center.longitude, center.latitude] : [116.397428, 39.90923],
        zoom: 13,
        resizeEnable: true,
      });
      console.log("地图实例创建成功:", mapInstance.current);

      // Add toolbar for zoom/pan
      window.AMap.plugin(['AMap.ToolBar', 'AMap.PlaceSearch', 'AMap.Driving'], function(){
        console.log("高德地图插件加载回调触发。");
        mapInstance.current.addControl(new window.AMap.ToolBar());
        console.log("ToolBar加载成功。");

        // 初始化 PlaceSearch
        const placeSearch = new window.AMap.PlaceSearch({
          pageSize: 20, // 单页显示结果条数
          pageIndex: 1, // 页码
          city: '全国', // 兴趣点城市
          map: mapInstance.current, // 展现结果的地图实例
          panel: '', // 结果列表将在此 DIV 中进行显示。默认值：''，不显示。
          autoFitView: true // 是否自动调整地图视野使绘制的路线处于视口的合适位置
        });
        console.log("PlaceSearch实例创建成功:", placeSearch);

        // 定义 drawRoute 函数，确保在导航插件可用时再使用
        const internalDrawRoute = (start, end, mode = 'driving') => {
          if (!mapInstance.current || !window.AMap) {
            console.error("地图或导航插件未准备好 (internalDrawRoute)。");
            return;
          }

          // 清除所有之前绘制的路线
          if (mapInstance.current.driving) mapInstance.current.driving.clear();
          if (mapInstance.current.walking) mapInstance.current.walking.clear();
          if (mapInstance.current.transit) mapInstance.current.transit.clear();

          let navigatorInstance;
          let NavigatorClass;

          switch (mode) {
            case 'walking':
              NavigatorClass = window.AMap.Walking;
              break;
            case 'transit':
              // 公交路线规划需要指定城市
              NavigatorClass = window.AMap.Transit;
              break;
            case 'driving':
            default:
              NavigatorClass = window.AMap.Driving;
              break;
          }
          
          if (!NavigatorClass) {
            console.error(`未找到 ${mode} 导航插件`);
            return;
          }

          // 根据官方示例精简配置，只保留地图和面板
          const navigatorOptions = {
            map: mapInstance.current,
            panel: 'panel', // 如果有用于显示文本指令的 div
            // showTraffic: true, // 仅适用于驾车，步行和公交无交通路况
            autoFitView: true
          };

          // 对于公交导航，可能需要额外的城市参数
          if (mode === 'transit') {
            // 默认城市为当前定位城市或全国，这里暂时使用'全国'
            // 理想情况下，city应该从location中获取或由用户选择
            navigatorOptions.city = '全国'; 
            navigatorOptions.policy = window.AMap.TransferPolicy ? window.AMap.TransferPolicy.LEAST_TIME : undefined;
          }

          // 实例化导航类
          navigatorInstance = new NavigatorClass(navigatorOptions);
          mapInstance.current[mode] = navigatorInstance; // 存储实例以便后续清除

          // 执行搜索
          navigatorInstance.search(
            new window.AMap.LngLat(start.longitude, start.latitude),
            new window.AMap.LngLat(end.longitude, end.latitude),
            function (status, result) {
              if (status === 'complete') {
                console.log(`绘制${mode}路线完成`, result);
                if (result.routes && result.routes.length) {
                  // 可以选择显示路线信息，例如里程、时间等
                }
              } else {
                console.error(`获取${mode}数据失败：` + result);
              }
            }
          );
        };

        // 当地图、PlaceSearch 和所有导航插件准备就绪时，通过 prop 回调给父组件
        // 注意：这里确保了所有插件都已在 AMap.plugin 回调中初始化，因此是安全的
        onMapLoaded(mapInstance.current, placeSearch, internalDrawRoute); // 传递 drawRoute
        console.log("onMapLoaded回调已触发，地图服务已准备就绪。");
      });

      // Display user's current location marker
      if (center) {
        const userMarker = new window.AMap.Marker({
          position: new window.AMap.LngLat(center.longitude, center.latitude),
          icon: '//a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-red.png',
          offset: new window.AMap.Pixel(-13, -30),
          title: '我的位置'
        });
        mapInstance.current.add(userMarker);
        mapInstance.current.setFitView();
      }
    };

    loadScript();

    return () => {
      if (mapInstance.current) {
        mapInstance.current.destroy();
      }
    };
  }, [center]);

  useEffect(() => {
    if (!mapInstance.current || !window.AMap) return;

    // Clear existing hospital markers
    mapInstance.current.remove(markers.current);
    markers.current = [];

    // Add hospital markers
    hospitals.forEach(hospital => {
      if (hospital.location && hospital.location.longitude && hospital.location.latitude) {
        const marker = new window.AMap.Marker({
          position: new window.AMap.LngLat(hospital.location.longitude, hospital.location.latitude),
          title: hospital.name,
          extData: hospital, // Store full hospital data
        });

        marker.on('click', (e) => {
          const clickedHospital = e.target.getExtData();
          alert(`点击了医院: ${clickedHospital.name}\n地址: ${clickedHospital.address}`);
          // You can also trigger navigation here: onNavigate(center, clickedHospital.location);
        });

        markers.current.push(marker);
      }
    });
    mapInstance.current.add(markers.current);
    if (markers.current.length > 0) {
        mapInstance.current.setFitView();
    }

  }, [hospitals]);

  return <div id="map-container" ref={mapRef} style={{ width: '100%', height: '500px' }} />;
};

export default MapDisplay; 