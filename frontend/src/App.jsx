import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { 
  MapPin, 
  Search, 
  Phone, 
  Star, 
  Navigation, 
  MessageCircle, 
  AlertTriangle,
  Heart,
  Thermometer,
  Activity,
  Clock,
  Hospital
} from 'lucide-react'
import AIChatPage from './components/AIChatPage.jsx'
import MapDisplay from './components/MapDisplay.jsx'
import './App.css'
import Joyride from 'react-joyride';

// 主页组件（HomePage）：这是应用的主要视图，包含症状分析和地图功能。
function HomePage() {
  // 症状相关状态
  const [symptoms, setSymptoms] = useState('')
  const [selectedSymptoms, setSelectedSymptoms] = useState([])
  const [severity, setSeverity] = useState('中等')
  const [duration, setDuration] = useState('1-2天')
  // 位置和地图相关状态
  const [location, setLocation] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [drawRoute, setDrawRoute] = useState(null)
  const [mapInstance, setMapInstance] = useState(null);
  const [placeSearchInstance, setPlaceSearchInstance] = useState(null);
  const [isMapServicesReady, setIsMapServicesReady] = useState(false);
  const [navigationMode, setNavigationMode] = useState('driving');

  // --- 用户导览相关状态和逻辑 ---
  // runTour 状态：控制导览是否运行。初始设置为 false，将在 useEffect 中根据 localStorage 判断是否启动。
  const [runTour, setRunTour] = useState(false);
  // steps 数组：定义导览的每一个步骤。每个步骤都包含：
  //   - target: CSS选择器，指向导览要高亮显示的DOM元素。这是关键，确保元素有唯一的ID。
  //   - content: 该步骤的提示内容，向用户解释功能。
  //   - disableBeacon: 设置为true，表示不显示初始的"信标"动画，直接显示步骤。
  //   - placement: 提示框相对于目标元素的位置（如'left', 'top'），优化视觉效果。
  const [steps, setSteps] = useState([
    {
      target: '#ai-doctor-button', // 指向右上角的"AI医生"按钮
      content: '点击这里进入AI医生咨询，您可以与AI医生对话，查询天气等信息。这是一个智能聊天界面，可以解答您的各种医疗问题。',
      disableBeacon: true,
      placement: 'left',
    },
    {
      target: '#symptom-description-card', // 指向症状描述的Card组件
      content: '在此区域您可以详细描述您的症状，并通过选择常见症状来快速输入。我们将智能分析并为您推荐附近的合适医院。这是本页面的核心功能。',
      disableBeacon: true,
      placement: 'top',
    },
    {
      target: '#map-navigation-section', // 指向地图导航区域的Card组件
      content: '这里将显示附近医院的地图信息和导航功能。我们正在努力开发更完善的路线规划功能，敬请期待！',
      disableBeacon: true,
      placement: 'top',
    },
  ]);

  // useEffect 钩子：在组件首次挂载时执行，用于判断是否显示导览。
  useEffect(() => {
    // 检查本地存储中是否有'hasVisitedApp'标记。
    // 这用于确保导览只在用户首次访问应用时显示一次，避免重复。
    const hasVisited = localStorage.getItem('hasVisitedApp');
    if (!hasVisited) { // 如果是首次访问
      setRunTour(true); // 设置runTour为true，启动导览
      localStorage.setItem('hasVisitedApp', 'true'); // 在本地存储中设置标记，避免下次再次显示
    }
  }, []); // 空数组表示只在组件挂载时运行一次

  // handleJoyrideCallback 函数：Joyride的回调函数，用于处理导览的状态变化。
  // 当导览完成（'finished'）或被跳过（'skipped'）时，将runTour设为false，停止导览。
  const handleJoyrideCallback = (data) => {
    const { status } = data; // 获取当前导览的状态
    const finishedStatuses = ['finished', 'skipped']; // 定义导览结束的状态

    if (finishedStatuses.includes(status)) {
      setRunTour(false); // 停止导览
    }
    // 调试用途：在控制台打印Joyride的调试信息，方便开发时观察导览行为。
    // console.log("Joyride Callback:", data);
  };

  // 常见症状列表，用于快捷选择
  const commonSymptoms = [
    '发热', '咳嗽', '头痛', '腹痛', '胸痛', 
    '恶心', '呕吐', '腹泻', '乏力', '失眠'
  ]

  // --- getUserLocation 函数改进定位精度 ---
  // 该函数用于获取用户的地理位置信息。
  const getUserLocation = () => {
    if (navigator.geolocation) { // 检查浏览器是否支持地理定位API
      navigator.geolocation.getCurrentPosition(
        (position) => { // 成功获取位置的回调函数
          // 更新 location 状态，存储获取到的纬度和经度。
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          })
        },
        (error) => { // 获取位置失败的回调函数
          console.error('获取位置失败:', error)
          // 获取位置失败时，使用北京作为默认位置，提供一个备用方案，确保应用仍能运行。
          setLocation({
            latitude: 39.9042,
            longitude: 116.4074
          })
        },
        // 配置选项：
        // enableHighAccuracy: true 请求浏览器使用最高精度的定位方法（例如GPS）。
        // timeout: 10000 设置获取位置的超时时间为10秒（10000毫秒）。如果在超时时间内未获取到，将触发错误回调。
        // maximumAge: 0 表示不使用缓存的旧位置信息，强制每次都获取最新位置，提高实时性。
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      )
    } else {
      // 如果浏览器不支持地理定位API，则直接使用北京作为默认位置。
      setLocation({
        latitude: 39.9042,
        longitude: 116.4074
      })
    }
  }

  // useEffect 钩子：在组件挂载时调用 getUserLocation，自动尝试获取用户位置。
  useEffect(() => {
    getUserLocation()
  }, [])

  // 添加症状函数：将新的症状添加到已选择症状列表中，避免重复。
  const addSymptom = (symptom) => {
    if (!selectedSymptoms.includes(symptom)) {
      setSelectedSymptoms([...selectedSymptoms, symptom])
    }
  }

  // 移除症状函数：从已选择症状列表中移除指定症状。
  const removeSymptom = (symptom) => {
    setSelectedSymptoms(selectedSymptoms.filter(s => s !== symptom))
  }

  // 分析症状函数：处理症状分析的提交逻辑，调用后端API。
  const analyzeSymptoms = async () => {
    // 输入校验：确保用户至少选择或输入了症状。
    if (selectedSymptoms.length === 0 && !symptoms.trim()) {
      alert('请至少选择一个症状或输入症状描述')
      return
    }

    // 地图服务就绪检查：确保高德地图服务已加载，否则无法进行医院搜索。
    if (!isMapServicesReady) {
      alert('高德地图服务正在加载中，请稍候再试。');
      return;
    }

    setIsAnalyzing(true) // 设置加载状态为true，显示加载指示器
    
    try {
      // 构建要发送给后端进行分析的症状列表：包含已选择症状和用户输入的详细症状。
      const symptomsToAnalyze = symptoms.trim() ? 
        [...selectedSymptoms, symptoms] : selectedSymptoms

      console.log('发送症状分析请求:', {
        symptoms: symptomsToAnalyze,
        severity,
        duration,
        additional_info: symptoms
      })

      // 发送POST请求到后端症状分析API。
      const analysisResponse = await fetch('/api/ai/health-advice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // 请求体包含症状、严重程度、持续时间和附加信息。
        body: JSON.stringify({
          symptoms: symptomsToAnalyze,
          severity,
          duration,
          additional_info: symptoms
        })
      })

      // 解析后端返回的JSON数据。
      const analysisData = await analysisResponse.json()
      console.log('症状分析结果:', analysisData)
      
      if (analysisData.success) {
        setAnalysisResult(analysisData.data) // 更新症状分析结果状态
      } else {
        alert('分析失败: ' + analysisData.error) // 显示错误信息
      }
    } catch (error) {
      console.error('分析错误:', error)
      alert('分析过程中出现错误，请稍后重试')
    } finally {
      setIsAnalyzing(false) // 无论成功或失败，都将加载状态设为false
    }
  }

  // useEffect 钩子：监听分析结果、位置、高德地图实例，触发医院搜索。
  useEffect(() => {
    // 只有当所有必需的条件都满足时，才执行医院搜索。
    if (analysisResult && location && placeSearchInstance && isMapServicesReady) {
      console.log('触发高德地图医院搜索 (useEffect):', {
        analysis_result: analysisResult,
        location: location,
        radius: 50000 // 搜索半径，例如50公里
      });

      // 调用高德地图的placeSearchInstance进行周边搜索。
      placeSearchInstance.searchNearBy(
        '医院', // 搜索关键词
        new window.AMap.LngLat(location.longitude, location.latitude), // 以用户当前位置为中心
        50000, // 搜索半径
        (status, result) => { // 搜索回调函数
          console.log('PlaceSearch 回调状态 (App.jsx):', status);
          console.log('PlaceSearch 回调结果 (App.jsx):', result);
          // 调试：检查poiList是否存在和内容
          if (result && result.poiList && result.poiList.pois) {
            console.log('PlaceSearch result.poiList 类型 (App.jsx):', typeof result.poiList.pois);
            console.log('PlaceSearch result.poiList 内容 (App.jsx):', result.poiList.pois);
          } else {
            console.log('PlaceSearch result.poiList 不存在或为空 (App.jsx).');
          }

          // 如果搜索成功且有结果
          if (status === 'complete' && result.poiList && result.poiList.pois) {
            const actualPois = result.poiList.pois;
            if (actualPois.length > 0) {
              console.log('医院推荐结果 (前端高德地图 - useEffect):', actualPois);
            } else {
              console.log('高德地图医院搜索成功，但未找到匹配医院。');
            }
            // 过滤并格式化医院数据，只保留医疗保健服务或医院类型的POI。
            const filteredHospitals = actualPois.filter(poi => poi.type.includes("医疗保健服务") || poi.type.includes("医院"))
              .map(poi => ({
                name: poi.name,
                address: poi.address,
                location: {
                  longitude: poi.location.lng,
                  latitude: poi.location.lat
                },
                tel: poi.tel,
                distance: poi.distance,
                type: poi.type
              }));
            setRecommendations(filteredHospitals); // 更新推荐医院列表
          } else {
            // 搜索失败或无结果，打印错误并清空推荐列表。
            console.error('高德地图医院搜索失败 (useEffect) - 状态或结果异常:', status, result);
            setRecommendations([]);
          }
        }
      );
    }
  }, [analysisResult, location, placeSearchInstance, isMapServicesReady]); // 依赖项列表，当这些状态变化时，effect会重新运行

  // --- JSX 渲染部分 ---
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-indigo-100">
      {console.log("DEBUG Render (HomePage): analysisResult =", analysisResult, ", recommendations =", recommendations)}
      {/* Joyride 组件：用户导览的核心组件。 */} 
      <Joyride
        run={runTour} // 控制导览是否运行，根据runTour状态决定。
        steps={steps} // 传入定义的导览步骤。
        callback={handleJoyrideCallback} // 导览状态变化时的回调函数。
        continuous={true} // 设置为true，导览将在每个步骤结束后自动前进。
        showProgress={true} // 显示导览进度（例如"1/3"）。
        showSkipButton={true} // 显示"跳过"按钮，允许用户跳过导览。
        styles={{
          options: {
            zIndex: 10000, // 设置z-index，确保导览蒙层和提示框显示在页面最上层。
          },
        }}
        locale={{ // 本地化导览按钮的文本，使其显示中文。
          back: '上一步',
          close: '关闭',
          last: '完成',
          next: '下一步',
          skip: '跳过',
        }}
        debug={true} // 启用调试模式，会在浏览器控制台输出详细的导览信息，方便调试。
      />
      {/* 头部区域 */}
      <header className="bg-white shadow-md border-b rounded-b-lg">
        <div className="max-w-7xl mx-auto px-6 sm:px-6 lg:px-8 py-5">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-2">
              <Heart className="h-8 w-8 text-red-500" />
              <h1 className="text-2xl font-bold text-gray-900">智能医疗助手</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link to="/ai-chat">
                {/* AI医生按钮：添加了id，作为Joyride的target，用于导览定位 */} 
                <Button variant="ghost" id="ai-doctor-button">
                  <MessageCircle className="h-5 w-5 mr-1" />
                  AI 医生
                </Button>
              </Link>
              <Badge variant="outline" className="text-green-600">
                <Activity className="h-4 w-4 mr-1" />
                服务正常
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-white rounded-xl shadow-md">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 症状输入区域 */}
          <div className="lg:col-span-2">
            {/* 症状描述卡片：添加了id，作为Joyride的target */} 
            <Card id="symptom-description-card" className="shadow-lg rounded-xl">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Thermometer className="h-5 w-5 text-blue-500" />
                  <span>症状描述</span>
                </CardTitle>
                <CardDescription>
                  请详细描述您的症状，我们将为您推荐合适的医院
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* 常见症状快捷选择区域 */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    常见症状（点击选择）
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {commonSymptoms.map((symptom) => (
                      <Badge
                        key={symptom}
                        variant={selectedSymptoms.includes(symptom) ? "default" : "outline"}
                        className="cursor-pointer hover:bg-blue-100 transition-colors"
                        onClick={() => 
                          selectedSymptoms.includes(symptom) 
                            ? removeSymptom(symptom) 
                            : addSymptom(symptom)
                        }
                      >
                        {symptom}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* 已选择的症状显示区域 */}
                {selectedSymptoms.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      已选择的症状
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {selectedSymptoms.map((symptom) => (
                        <Badge key={symptom} variant="default" className="cursor-pointer rounded-full shadow-sm">
                          {symptom}
                          <button
                            onClick={() => removeSymptom(symptom)}
                            className="ml-1 text-xs hover:text-red-500"
                          >
                            ×
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* 详细症状描述文本框 */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    详细症状描述（可选）
                  </label>
                  <Textarea
                    placeholder="请详细描述您的症状，包括发生时间、严重程度等..."
                    value={symptoms}
                    onChange={(e) => setSymptoms(e.target.value)}
                    rows={3}
                  />
                </div>

                {/* 严重程度和持续时间选择 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      严重程度
                    </label>
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="轻微">轻微</option>
                      <option value="中等">中等</option>
                      <option value="严重">严重</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      持续时间
                    </label>
                    <select
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="几小时">几小时</option>
                      <option value="1-2天">1-2天</option>
                      <option value="3-7天">3-7天</option>
                      <option value="超过一周">超过一周</option>
                    </select>
                  </div>
                </div>

                {/* 分析按钮 */}
                <div className="flex justify-end mt-6">
                  {console.log("DEBUG Frontend: isAnalyzing = ", isAnalyzing, ", isMapServicesReady = ", isMapServicesReady)}
                  <Button onClick={analyzeSymptoms} disabled={isAnalyzing || !isMapServicesReady}>
                    {isAnalyzing ? '分析中...' : '分析症状并获取推荐'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 侧边栏 - 位置信息和紧急联系 */}
          <div className="space-y-6">
            {/* 位置信息卡片 */}
            <Card className="shadow-lg rounded-xl">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <MapPin className="h-5 w-5 text-green-500" />
                  <span>位置信息</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {location ? (
                  <div className="text-sm text-gray-600">
                    <p>纬度: {location.latitude.toFixed(4)}</p>
                    <p>经度: {location.longitude.toFixed(4)}</p>
                    <p className="text-green-600 mt-2">✓ 位置已获取</p>
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">
                    <p>正在获取位置信息...</p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={getUserLocation}
                      className="mt-2"
                    >
                      重新获取位置
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 紧急联系卡片 */}
            <Card className="border-l-4 border-red-500 bg-red-50 shadow-lg rounded-xl">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-red-600">
                  <AlertTriangle className="h-5 w-5" />
                  <span>紧急联系</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">急救电话</span>
                  <Badge variant="outline">120</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">猛男热线</span>
                  <Badge variant="outline">137-7840-4583</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">心理热线</span>
                  <Badge variant="outline">400-161-9995</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* 分析结果和医院推荐区域（Tabs组件） */}
        {analysisResult && (
          <>
            {console.log("DEBUG Render (Tabs): analysisResult is truthy, rendering Tabs.")}
            <div className="mt-8">
              <Tabs defaultValue="analysis" className="w-full">
                <TabsList className="grid w-full grid-cols-2 shadow-md rounded-lg">
                  <TabsTrigger value="analysis">症状分析</TabsTrigger>
                  <TabsTrigger value="hospitals">医院推荐</TabsTrigger>
                </TabsList>
                
                {/* 症状分析内容面板 */}
                <TabsContent value="analysis" className="mt-6">
                  <Card className="shadow-lg rounded-xl">
                    <CardHeader>
                      <CardTitle>症状分析结果</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* 紧急程度显示 */}
                      <Alert className={
                        analysisResult.urgency_level === '高' ? 'border-red-500 bg-red-50 shadow-sm' :
                        analysisResult.urgency_level === '中' ? 'border-yellow-500 bg-yellow-50 shadow-sm' :
                        'border-green-500 bg-green-50 shadow-sm'
                      }>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>
                          <strong>紧急程度: {analysisResult.urgency_level}</strong>
                          {analysisResult.urgency_level === '高' && ' - 建议立即就医！'}
                          {analysisResult.urgency_level === '中' && ' - 建议尽快就医'}
                          {analysisResult.urgency_level === '低' && ' - 可先观察，必要时就医'}
                        </AlertDescription>
                      </Alert>

                      {/* 可能疾病列表 */}
                      <div>
                        <h4 className="font-medium mb-2">可能的疾病</h4>
                        <div className="space-y-2">
                          {analysisResult.analysis.possible_diseases?.map((disease, index) => (
                            <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded shadow-sm">
                              <span>{disease.name}</span>
                              <Badge variant="outline">
                                匹配度: {(disease.confidence * 100).toFixed(0)}%
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 推荐科室列表 */}
                      <div>
                        <h4 className="font-medium mb-2">推荐科室</h4>
                        <div className="flex flex-wrap gap-2">
                          {analysisResult.analysis.recommended_departments?.map((dept, index) => (
                            <Badge key={index} variant="secondary" className="shadow-sm">{dept}</Badge>
                          ))}
                        </div>
                      </div>

                      {/* 医疗建议列表 */}
                      <div>
                        <h4 className="font-medium mb-2">医疗建议</h4>
                        <ul className="space-y-1 text-sm text-gray-600">
                          {analysisResult.analysis.advice?.map((advice, index) => (
                            <li key={index} className="flex items-start space-x-2">
                              <span className="text-blue-500 mt-1">•</span>
                              <span>{advice}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* 医院推荐内容面板 */}
                <TabsContent value="hospitals" className="mt-6">
                  <div className="space-y-4">
                    {/* 推荐医院列表 */}
                    {recommendations.length > 0 ? (
                      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        <h3 className="text-lg font-semibold col-span-full">推荐医院:</h3>
                        {recommendations.map((hospital, index) => (
                          <Card key={index} className="p-3 flex items-center justify-between shadow-sm rounded-lg">
                            <div>
                              <p className="font-medium">{hospital.name}</p>
                              <p className="text-sm text-gray-500">{hospital.address}</p>
                              {hospital.distance && (
                                <p className="text-xs text-gray-400">距离: {(hospital.distance / 1000).toFixed(2)} 公里</p>
                              )}
                              {hospital.type && (
                                <Badge variant="secondary" className="mt-1 text-xs shadow-sm">
                                  {hospital.type.split(';')[1] || hospital.type.split(';')[0]}
                                </Badge>
                              )}
                            </div>
                            <Button variant="outline" size="sm" onClick={() => drawRoute && drawRoute(location, hospital.location)}>
                              <Navigation className="h-4 w-4 mr-1" />导航
                            </Button>
                          </Card>
                        ))}
                      </div>
                    ) : (
                      <Card className="shadow-lg rounded-xl">
                        <CardContent className="p-6 text-center text-gray-500">
                          <Hospital className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                          <p>暂无医院推荐，请先进行症状分析</p>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </>
        )}
      </main>
      {/* 地图显示区域：仅当 location 存在时显示 */}
      {location && (
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          {/* 地图导航区域卡片：添加了id，作为Joyride的target */} 
          <Card id="map-navigation-section" className="shadow-lg rounded-xl">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <MapPin className="h-5 w-5 text-blue-500" />
                <span>附近医院地图</span>
              </CardTitle>
              <CardDescription>
                在地图上查看您的位置和推荐医院
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MapDisplay 
                center={location}
                hospitals={recommendations}
                onNavigate={setDrawRoute}
                onMapLoaded={(map, placeSearch, drawRouteCallback) => {
                  setMapInstance(map);
                  setPlaceSearchInstance(placeSearch);
                  setDrawRoute(() => drawRouteCallback);
                  setIsMapServicesReady(true);
                }}
              />
              <div id="panel" className="mt-4" style={{ height: '300px', overflow: 'auto', border: '1px solid #eee' }}>
                {/* 导航路线详情将显示在这里 */}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// App 函数组件：应用的根组件，配置了React Router的路由。
function App() {
  return (
    <Router> {/* BrowserRouter：使用HTML5 history API来保持UI与URL同步 */} 
      <Routes> {/* Routes：包含所有路由定义的容器 */} 
        <Route path="/" element={<HomePage />} /> {/* 根路径路由到 HomePage 组件 */} 
        <Route path="/ai-chat" element={<AIChatPage />} /> {/* /ai-chat 路径路由到 AIChatPage 组件 */} 
      </Routes>
    </Router>
  );
}

export default App

