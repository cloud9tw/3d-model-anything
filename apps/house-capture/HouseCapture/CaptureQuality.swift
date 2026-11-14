import Foundation

enum CaptureScope: String, CaseIterable, Identifiable {
  case area, room
  var id: String { rawValue }
  var label: String { self == .area ? "Partial area" : "Whole room" }
}

/// Pure policies: guidance never prevents saving partial work.
struct CaptureQuality {
  let percent: Int
  let walls: Int
  let photos: Int
  var scope: CaptureScope = .area
  var ready: Bool {
    scope == .area ? photos > 0 : walls >= 3 && photos >= 8 && percent >= 85
  }
  var message: String {
    if scope == .area {
      return photos > 0
        ? "Photos collected. Save this area and review it; missing dimensions remain unmeasured."
        : "Capture the area you need, then save. You do not need three walls or full photo coverage."
    }
    if walls < 3 { return "Measuring the room and saving photos automatically." }
    if photos < 8 { return "Collecting useful viewpoints automatically as you scan." }
    if ready { return "Good photo detail. Save and review for gaps." }
    return "Photos are saved automatically as you move around the room."
  }
}

/// Reserve before starting a JPEG write; failures release the slot. Manual shots
/// never enter this budget. One pending write also bounds memory use.
struct AutomaticPhotoBudget {
  let limit: Int
  private(set) var saved = 0
  private(set) var pending = 0

  init(limit: Int = 60) { self.limit = max(0, limit) }
  var canReserve: Bool { pending == 0 && saved < limit }
  mutating func reserve() -> Bool {
    guard canReserve else { return false }
    pending += 1
    return true
  }
  mutating func complete(saved succeeded: Bool) {
    guard pending > 0 else { return }
    pending -= 1
    if succeeded { saved += 1 }
  }
}

struct CaptureBudget {
  let constrained: Bool
  let critical: Bool
  init(thermal: ProcessInfo.ThermalState, photos: Int, memoryPressure: Bool) {
    critical = thermal == .critical
    constrained = memoryPressure || photos >= 150 || thermal == .serious || critical
  }
  var depthInterval: Double { critical ? 1 : constrained ? 0.5 : 0.2 }
  var evaluationInterval: Double { constrained ? 0.3 : 0.1 }
  var photoInterval: Double { constrained ? 1.2 : 0.4 }
}
