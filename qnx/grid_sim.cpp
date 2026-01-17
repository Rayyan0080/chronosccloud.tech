/**
 * QNX Grid Simulator
 * 
 * Simulates a QNX-based power grid monitoring system.
 * Emits newline-delimited JSON power events to stdout every 5 seconds.
 * 
 * Compile: g++ -o grid_sim grid_sim.cpp -std=c++11
 * Run: ./grid_sim
 */

#include <iostream>
#include <iomanip>
#include <chrono>
#include <thread>
#include <random>
#include <sstream>
#include <ctime>

// Sector IDs
const char* SECTORS[] = {"sector-1", "sector-2", "sector-3"};
const int NUM_SECTORS = 3;

// Voltage ranges (normal: 110-130V, failure: 0-50V)
const double NORMAL_VOLTAGE_MIN = 110.0;
const double NORMAL_VOLTAGE_MAX = 130.0;
const double FAILURE_VOLTAGE_MIN = 0.0;
const double FAILURE_VOLTAGE_MAX = 50.0;

// Load range (0-100%)
const double LOAD_MIN = 0.0;
const double LOAD_MAX = 100.0;

// Event interval (5 seconds)
const int EVENT_INTERVAL_SEC = 5;

/**
 * Get current timestamp in ISO 8601 format
 */
std::string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()
    ) % 1000;

    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    ss << "." << std::setfill('0') << std::setw(3) << ms.count() << "Z";
    return ss.str();
}

/**
 * Generate a power event for a sector
 */
void emitPowerEvent(const char* sector_id, std::mt19937& gen) {
    // Random voltage (simulate occasional failures)
    std::uniform_real_distribution<double> voltage_dist(0.0, 130.0);
    double voltage = voltage_dist(gen);
    
    // If voltage is low, it's a failure scenario
    bool is_failure = voltage < 50.0;
    
    // Random load
    std::uniform_real_distribution<double> load_dist(LOAD_MIN, LOAD_MAX);
    double load = load_dist(gen);

    // Create JSON event
    std::cout << "{"
              << "\"sector_id\":\"" << sector_id << "\","
              << "\"voltage\":" << std::fixed << std::setprecision(2) << voltage << ","
              << "\"load\":" << std::fixed << std::setprecision(2) << load << ","
              << "\"timestamp\":\"" << getCurrentTimestamp() << "\","
              << "\"status\":" << (is_failure ? "\"failure\"" : "\"normal\"")
              << "}" << std::endl;
    
    std::cout.flush();
}

int main() {
    // Seed random number generator
    std::random_device rd;
    std::mt19937 gen(rd());

    std::cerr << "[QNX] Grid Simulator started" << std::endl;
    std::cerr << "[QNX] Emitting power events every " << EVENT_INTERVAL_SEC << " seconds" << std::endl;
    std::cerr << "[QNX] Sectors: sector-1, sector-2, sector-3" << std::endl;
    std::cerr << "[QNX] Deterministic loop" << std::endl;

    int cycle = 0;

    while (true) {
        cycle++;
        
        // Log deterministic loop
        std::cerr << "[QNX] deterministic loop - cycle " << cycle << std::endl;

        // Emit event for each sector
        for (int i = 0; i < NUM_SECTORS; i++) {
            emitPowerEvent(SECTORS[i], gen);
        }

        // Wait 5 seconds before next cycle
        std::this_thread::sleep_for(std::chrono::seconds(EVENT_INTERVAL_SEC));
    }

    return 0;
}

