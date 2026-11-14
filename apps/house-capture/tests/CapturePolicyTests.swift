import Foundation

@main
struct CapturePolicyTests {
  static func expect(_ value: @autoclosure () -> Bool, _ message: String) {
    guard value() else { print("FAIL: \(message)"); exit(1) }
  }

  static func main() {
    // A corner with useful photos must not require three walls or 85% coverage.
    let partial = CaptureQuality(percent: 20, walls: 1, photos: 4)
    guard partial.ready else {
      print("FAIL: a partial area with photos should be ready for review")
      exit(1)
    }
    expect(!CaptureQuality(percent: 100, walls: 0, photos: 0).ready, "empty capture is not useful evidence")
    expect(!CaptureQuality(percent: 20, walls: 1, photos: 4, scope: .room).ready, "full room guidance still requires room evidence")
    expect(CaptureQuality(percent: 88, walls: 4, photos: 20, scope: .room).ready, "room guidance accepts sufficient measured coverage")
    expect(!CaptureQuality(percent: 20, walls: 4, photos: 201, scope: .room).ready, "photo count does not hide missing coverage")

    var budget = AutomaticPhotoBudget()
    for _ in 0..<60 {
      expect(budget.reserve(), "an automatic photo within the budget is admitted")
      expect(!budget.reserve(), "a pending JPEG prevents another admission")
      budget.complete(saved: true)
    }
    expect(!budget.reserve(), "the 61st automatic photo is rejected")
    expect(budget.saved == 60 && budget.pending == 0, "only completed JPEGs consume the quota")
    budget = AutomaticPhotoBudget(limit: 1)
    expect(budget.reserve(), "new room resets the quota")
    budget.complete(saved: false)
    expect(budget.saved == 0 && budget.reserve(), "a failed JPEG write can be retried")
    budget.complete(saved: true)
    budget.complete(saved: true)
    expect(budget.saved == 1 && !budget.canReserve, "a duplicate completion cannot consume another slot")
    expect(!AutomaticPhotoBudget(limit: 0).canReserve, "zero disables automatic photos")
    expect(!AutomaticPhotoBudget(limit: -1).canReserve, "negative input cannot enable capture")
    print("Capture policy tests passed")
  }
}
