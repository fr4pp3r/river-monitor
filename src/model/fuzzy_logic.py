"""
Fuzzy Logic Module for River Monitor System
Implements fuzzy inference system for flood risk classification
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Dict, Tuple, Optional
import json

from src.config import (
    WL_THRESHOLDS, FRAIN_THRESHOLDS, ROR_THRESHOLDS, TIDE_THRESHOLDS,
    RF_PROPENSITY_MAP, RISK_LEVELS
)


class FuzzyFloodRisk:
    """Fuzzy inference system for flood risk classification"""
    
    def __init__(self):
        self.system = None
        self.simulation = None
        self._build_system()
    
    def _build_system(self):
        """Build the fuzzy control system with all variables and rules"""
        
        # =========================================================================
        # INPUT VARIABLES
        # =========================================================================
        
        # Water Level (mm) - universe: 0 to 3000
        self.wl = ctrl.Antecedent(np.arange(0, 3001, 1), 'water_level')
        self.wl['Low'] = fuzz.trapmf(self.wl.universe, [0, 0, 300, WL_THRESHOLDS['low_max']])
        self.wl['Medium'] = fuzz.trimf(self.wl.universe, [WL_THRESHOLDS['medium_min'], 
                                                          (WL_THRESHOLDS['medium_min'] + WL_THRESHOLDS['medium_max']) / 2, 
                                                          WL_THRESHOLDS['medium_max']])
        self.wl['High'] = fuzz.trimf(self.wl.universe, [WL_THRESHOLDS['high_min'], 
                                                        (WL_THRESHOLDS['high_min'] + WL_THRESHOLDS['high_max']) / 2, 
                                                        WL_THRESHOLDS['high_max']])
        self.wl['Very High'] = fuzz.trapmf(self.wl.universe, [WL_THRESHOLDS['very_high_min'], 2000, 3000, 3000])
        
        # Rate of Rise (mm/day) - universe: -1000 to 1000
        self.ror = ctrl.Antecedent(np.arange(-1000, 1001, 1), 'rate_of_rise')
        self.ror['Negative'] = fuzz.trapmf(self.ror.universe, [-1000, -1000, -100, ROR_THRESHOLDS['negative_max']])
        self.ror['Near-Zero'] = fuzz.trimf(self.ror.universe, [ROR_THRESHOLDS['near_zero_min'], 0, ROR_THRESHOLDS['near_zero_max']])
        self.ror['Moderate'] = fuzz.trimf(self.ror.universe, [ROR_THRESHOLDS['moderate_min'], 
                                                              (ROR_THRESHOLDS['moderate_min'] + ROR_THRESHOLDS['moderate_max']) / 2, 
                                                              ROR_THRESHOLDS['moderate_max']])
        self.ror['Rapid'] = fuzz.trapmf(self.ror.universe, [ROR_THRESHOLDS['rapid_min'], 200, 1000, 1000])
        
        # Forecast Rain (mm/day) - universe: 0 to 100
        self.frain = ctrl.Antecedent(np.arange(0, 101, 1), 'forecast_rain')
        self.frain['None'] = fuzz.trapmf(self.frain.universe, [0, 0, 0, FRAIN_THRESHOLDS['none_max']])
        self.frain['Light'] = fuzz.trimf(self.frain.universe, [FRAIN_THRESHOLDS['light_min'], 
                                                                (FRAIN_THRESHOLDS['light_min'] + FRAIN_THRESHOLDS['light_max']) / 2, 
                                                                FRAIN_THRESHOLDS['light_max']])
        self.frain['Moderate'] = fuzz.trimf(self.frain.universe, [FRAIN_THRESHOLDS['moderate_min'], 
                                                                   (FRAIN_THRESHOLDS['moderate_min'] + FRAIN_THRESHOLDS['moderate_max']) / 2, 
                                                                   FRAIN_THRESHOLDS['moderate_max']])
        self.frain['Heavy'] = fuzz.trapmf(self.frain.universe, [FRAIN_THRESHOLDS['heavy_min'], 40, 100, 100])
        
        # Tide Level (meters) - universe: 0 to 5
        self.tide = ctrl.Antecedent(np.arange(0, 5.01, 0.01), 'tide_level')
        self.tide['Low'] = fuzz.trapmf(self.tide.universe, [0, 0, 0.25, TIDE_THRESHOLDS['low_max']])
        self.tide['Mid'] = fuzz.trimf(self.tide.universe, [TIDE_THRESHOLDS['mid_min'], 
                                                           (TIDE_THRESHOLDS['mid_min'] + TIDE_THRESHOLDS['mid_max']) / 2, 
                                                           TIDE_THRESHOLDS['mid_max']])
        self.tide['High'] = fuzz.trimf(self.tide.universe, [TIDE_THRESHOLDS['high_min'], 
                                                            (TIDE_THRESHOLDS['high_min'] + TIDE_THRESHOLDS['high_max']) / 2, 
                                                            TIDE_THRESHOLDS['high_max']])
        self.tide['Extreme'] = fuzz.trapmf(self.tide.universe, [TIDE_THRESHOLDS['extreme_min'], 3.5, 5.0, 5.0])
        
        # RF Flood Propensity (crisp 0, 1, 2) - universe: 0 to 2
        self.rf = ctrl.Antecedent(np.arange(0, 2.01, 0.01), 'rf_propensity')
        self.rf['Low'] = fuzz.trimf(self.rf.universe, [0, 0, 0.5])
        self.rf['Medium'] = fuzz.trimf(self.rf.universe, [0.5, 1, 1.5])
        self.rf['High'] = fuzz.trimf(self.rf.universe, [1.5, 2, 2])
        
        # =========================================================================
        # OUTPUT VARIABLE
        # =========================================================================
        
        # Flood Risk Level - universe: 0 to 6
        self.risk = ctrl.Consequent(np.arange(0, 6.01, 0.01), 'flood_risk')
        self.risk['Receding'] = fuzz.trimf(self.risk.universe, [0, 0, 1])
        self.risk['Alert'] = fuzz.trimf(self.risk.universe, [1, 2, 3])
        self.risk['Alarm'] = fuzz.trimf(self.risk.universe, [3, 4, 5])
        self.risk['Critical'] = fuzz.trimf(self.risk.universe, [5, 6, 6])
        
        # =========================================================================
        # RULES (from the 15-rule table)
        # =========================================================================
        
        rules = []
        
        # Rule 1: Low WL, Negative RoR, None-Light FRain, Low-Mid Tide, Low RF -> Receding
        rules.append(ctrl.Rule(
            self.wl['Low'] & self.ror['Negative'] & 
            (self.frain['None'] | self.frain['Light']) & 
            (self.tide['Low'] | self.tide['Mid']) & 
            self.rf['Low'],
            self.risk['Receding']
        ))
        
        # Rule 2: Low WL, Near-Zero RoR, None-Light FRain, Low-Mid Tide, Low RF -> Receding
        rules.append(ctrl.Rule(
            self.wl['Low'] & self.ror['Near-Zero'] & 
            (self.frain['None'] | self.frain['Light']) & 
            (self.tide['Low'] | self.tide['Mid']) & 
            self.rf['Low'],
            self.risk['Receding']
        ))
        
        # Rule 3: Low-Medium WL, Near-Zero RoR, Light FRain, Low-Mid Tide, Low RF -> Receding
        rules.append(ctrl.Rule(
            (self.wl['Low'] | self.wl['Medium']) & self.ror['Near-Zero'] & 
            self.frain['Light'] & 
            (self.tide['Low'] | self.tide['Mid']) & 
            self.rf['Low'],
            self.risk['Receding']
        ))
        
        # Rule 4: Low-Medium WL, Moderate RoR, Light-Moderate FRain, Low-Mid Tide, Low RF -> Alert
        rules.append(ctrl.Rule(
            (self.wl['Low'] | self.wl['Medium']) & self.ror['Moderate'] & 
            (self.frain['Light'] | self.frain['Moderate']) & 
            (self.tide['Low'] | self.tide['Mid']) & 
            self.rf['Low'],
            self.risk['Alert']
        ))
        
        # Rule 5: Medium WL, Moderate RoR, Moderate FRain, Mid Tide, Low RF -> Alert
        rules.append(ctrl.Rule(
            self.wl['Medium'] & self.ror['Moderate'] & 
            self.frain['Moderate'] & 
            self.tide['Mid'] & 
            self.rf['Low'],
            self.risk['Alert']
        ))
        
        # Rule 6: Medium WL, Moderate RoR, Moderate-Heavy FRain, Mid-High Tide, Medium RF -> Alarm
        rules.append(ctrl.Rule(
            self.wl['Medium'] & self.ror['Moderate'] & 
            (self.frain['Moderate'] | self.frain['Heavy']) & 
            (self.tide['Mid'] | self.tide['High']) & 
            self.rf['Medium'],
            self.risk['Alarm']
        ))
        
        # Rule 7: Medium-High WL, Rapid RoR, Moderate-Heavy FRain, Mid-High Tide, Medium RF -> Alarm
        rules.append(ctrl.Rule(
            (self.wl['Medium'] | self.wl['High']) & self.ror['Rapid'] & 
            (self.frain['Moderate'] | self.frain['Heavy']) & 
            (self.tide['Mid'] | self.tide['High']) & 
            self.rf['Medium'],
            self.risk['Alarm']
        ))
        
        # Rule 8: High WL, Rapid RoR, Heavy FRain, High-Extreme Tide, High RF -> Critical
        rules.append(ctrl.Rule(
            self.wl['High'] & self.ror['Rapid'] & 
            self.frain['Heavy'] & 
            (self.tide['High'] | self.tide['Extreme']) & 
            self.rf['High'],
            self.risk['Critical']
        ))
        
        # Rule 9: High WL, Near-Zero RoR, None-Light FRain, Mid Tide, Low RF -> Alert
        rules.append(ctrl.Rule(
            self.wl['High'] & self.ror['Near-Zero'] & 
            (self.frain['None'] | self.frain['Light']) & 
            self.tide['Mid'] & 
            self.rf['Low'],
            self.risk['Alert']
        ))
        
        # Rule 10: High WL, Near-Zero RoR, Moderate+ FRain, Mid-High Tide, Medium RF -> Alarm
        rules.append(ctrl.Rule(
            self.wl['High'] & self.ror['Near-Zero'] & 
            (self.frain['Moderate'] | self.frain['Heavy']) & 
            (self.tide['Mid'] | self.tide['High']) & 
            self.rf['Medium'],
            self.risk['Alarm']
        ))
        
        # Rule 11: Very High WL, Any RoR, Any FRain, Any Tide, Any RF -> Critical (safety override)
        rules.append(ctrl.Rule(
            self.wl['Very High'],
            self.risk['Critical']
        ))
        
        # Rule 12: Low-Medium WL, Negative RoR, Moderate+ FRain, Mid-High Tide, High RF -> Alert
        rules.append(ctrl.Rule(
            (self.wl['Low'] | self.wl['Medium']) & self.ror['Negative'] & 
            (self.frain['Moderate'] | self.frain['Heavy']) & 
            (self.tide['Mid'] | self.tide['High']) & 
            self.rf['High'],
            self.risk['Alert']
        ))
        
        # Rule 13: Medium WL, Negative RoR, Heavy FRain, High Tide, High RF -> Alarm
        rules.append(ctrl.Rule(
            self.wl['Medium'] & self.ror['Negative'] & 
            self.frain['Heavy'] & 
            self.tide['High'] & 
            self.rf['High'],
            self.risk['Alarm']
        ))
        
        # Rule 14: Medium-High WL, Moderate RoR, Moderate FRain, High Tide, High RF -> Alarm
        rules.append(ctrl.Rule(
            (self.wl['Medium'] | self.wl['High']) & self.ror['Moderate'] & 
            self.frain['Moderate'] & 
            self.tide['High'] & 
            self.rf['High'],
            self.risk['Alarm']
        ))
        
        # Rule 15: High WL, Moderate RoR, Moderate+ FRain, High Tide, High RF -> Critical
        rules.append(ctrl.Rule(
            self.wl['High'] & self.ror['Moderate'] & 
            (self.frain['Moderate'] | self.frain['Heavy']) & 
            self.tide['High'] & 
            self.rf['High'],
            self.risk['Critical']
        ))
        
        # Create control system
        self.system = ctrl.ControlSystem(rules)
        self.simulation = ctrl.ControlSystemSimulation(self.system)
    
    def compute_risk(self, water_level_mm: float, rate_of_rise_mm_day: float, 
                     forecast_rain_mm: float, tide_level_m: float, 
                     rf_propensity: int) -> Dict:
        """
        Compute flood risk using fuzzy inference
        
        Args:
            water_level_mm: Current water level in mm
            rate_of_rise_mm_day: Rate of rise in mm/day
            forecast_rain_mm: Forecasted precipitation in mm/day
            tide_level_m: Current tide level in meters
            rf_propensity: RF model output (0=Low, 1=Medium, 2=High)
        
        Returns:
            Dictionary with risk level, crisp output, and membership degrees
        """
        # Clip inputs to universe ranges
        wl = np.clip(water_level_mm, 0, 3000)
        ror = np.clip(rate_of_rise_mm_day, -1000, 1000)
        frain = np.clip(forecast_rain_mm, 0, 100)
        tide = np.clip(tide_level_m, 0, 5)
        rf = np.clip(rf_propensity, 0, 2)
        
        # Set inputs
        self.simulation.input['water_level'] = wl
        self.simulation.input['rate_of_rise'] = ror
        self.simulation.input['forecast_rain'] = frain
        self.simulation.input['tide_level'] = tide
        self.simulation.input['rf_propensity'] = rf
        
        # Compute
        try:
            self.simulation.compute()
            risk_crisp = self.simulation.output['flood_risk']
        except Exception as e:
            print(f"Fuzzy computation error: {e}")
            # Fallback: simple threshold-based
            risk_crisp = self._fallback_risk(wl, ror, frain, tide, rf)
        
        # Determine risk level from crisp output
        if risk_crisp < 1.5:
            risk_level = 'Receding'
        elif risk_crisp < 3.0:
            risk_level = 'Alert'
        elif risk_crisp < 4.5:
            risk_level = 'Alarm'
        else:
            risk_level = 'Critical'
        
        # Get membership degrees for all inputs
        memberships = self._get_memberships(wl, ror, frain, tide, rf)
        
        # Determine which rule fired (approximate)
        rule_triggered = self._estimate_rule(wl, ror, frain, tide, rf)
        
        return {
            'risk_level': risk_level,
            'risk_crisp': round(risk_crisp, 2),
            'memberships': memberships,
            'rule_triggered': rule_triggered,
            'inputs': {
                'water_level_mm': wl,
                'rate_of_rise_mm_day': round(ror, 1),
                'forecast_rain_mm': round(frain, 1),
                'tide_level_m': round(tide, 2),
                'rf_propensity': RF_PROPENSITY_MAP.get(rf, 'Unknown')
            }
        }
    
    def _get_memberships(self, wl: float, ror: float, frain: float, 
                         tide: float, rf: float) -> Dict:
        """Get membership degrees for all input terms"""
        memberships = {}
        
        # Water Level
        for term in ['Low', 'Medium', 'High', 'Very High']:
            memberships[f'WL_{term}'] = round(fuzz.interp_membership(
                self.wl.universe, self.wl[term].mf, wl), 3)
        
        # Rate of Rise
        for term in ['Negative', 'Near-Zero', 'Moderate', 'Rapid']:
            memberships[f'RoR_{term}'] = round(fuzz.interp_membership(
                self.ror.universe, self.ror[term].mf, ror), 3)
        
        # Forecast Rain
        for term in ['None', 'Light', 'Moderate', 'Heavy']:
            memberships[f'FRain_{term}'] = round(fuzz.interp_membership(
                self.frain.universe, self.frain[term].mf, frain), 3)
        
        # Tide Level
        for term in ['Low', 'Mid', 'High', 'Extreme']:
            memberships[f'Tide_{term}'] = round(fuzz.interp_membership(
                self.tide.universe, self.tide[term].mf, tide), 3)
        
        # RF Propensity
        for term in ['Low', 'Medium', 'High']:
            memberships[f'RF_{term}'] = round(fuzz.interp_membership(
                self.rf.universe, self.rf[term].mf, rf), 3)
        
        return memberships
    
    def _estimate_rule(self, wl: float, ror: float, frain: float, 
                       tide: float, rf: float) -> int:
        """Estimate which rule most likely fired based on input values"""
        # Simple heuristic based on dominant terms
        wl_term = self._get_dominant_term(wl, self.wl, ['Low', 'Medium', 'High', 'Very High'])
        ror_term = self._get_dominant_term(ror, self.ror, ['Negative', 'Near-Zero', 'Moderate', 'Rapid'])
        frain_term = self._get_dominant_term(frain, self.frain, ['None', 'Light', 'Moderate', 'Heavy'])
        tide_term = self._get_dominant_term(tide, self.tide, ['Low', 'Mid', 'High', 'Extreme'])
        rf_term = self._get_dominant_term(rf, self.rf, ['Low', 'Medium', 'High'])
        
        # Map to rule number (simplified)
        rule_map = {
            ('Low', 'Negative', 'None', 'Low', 'Low'): 1,
            ('Low', 'Negative', 'Light', 'Low', 'Low'): 1,
            ('Low', 'Near-Zero', 'None', 'Low', 'Low'): 2,
            ('Low', 'Near-Zero', 'Light', 'Low', 'Low'): 2,
            ('Medium', 'Near-Zero', 'Light', 'Low', 'Low'): 3,
            ('Low', 'Moderate', 'Light', 'Low', 'Low'): 4,
            ('Medium', 'Moderate', 'Light', 'Low', 'Low'): 4,
            ('Medium', 'Moderate', 'Moderate', 'Mid', 'Low'): 5,
            ('Medium', 'Moderate', 'Moderate', 'Mid', 'Medium'): 6,
            ('Medium', 'Moderate', 'Heavy', 'High', 'Medium'): 6,
            ('High', 'Rapid', 'Heavy', 'High', 'High'): 8,
            ('High', 'Near-Zero', 'None', 'Mid', 'Low'): 9,
            ('High', 'Near-Zero', 'Moderate', 'High', 'Medium'): 10,
            ('Very High', 'Any', 'Any', 'Any', 'Any'): 11,
        }
        
        key = (wl_term, ror_term, frain_term, tide_term, rf_term)
        return rule_map.get(key, 0)
    
    def _get_dominant_term(self, value: float, var: ctrl.Antecedent, terms: list) -> str:
        """Get the term with highest membership for a value"""
        max_membership = -1
        dominant = terms[0]
        for term in terms:
            mf = fuzz.interp_membership(var.universe, var[term].mf, value)
            if mf > max_membership:
                max_membership = mf
                dominant = term
        return dominant
    
    def _fallback_risk(self, wl: float, ror: float, frain: float, 
                       tide: float, rf: float) -> float:
        """Fallback risk calculation if fuzzy inference fails"""
        # Simple weighted scoring
        score = 0
        
        # Water level contribution (0-2)
        if wl >= 1830:
            score += 2.5
        elif wl >= 1220:
            score += 1.5
        elif wl >= 610:
            score += 0.5
        
        # Rate of rise contribution (0-1.5)
        if ror >= 100:
            score += 1.5
        elif ror >= 10:
            score += 1.0
        elif ror <= -10:
            score -= 0.5
        
        # Forecast rain contribution (0-1.5)
        if frain >= 30:
            score += 1.5
        elif frain >= 15:
            score += 1.0
        elif frain >= 5:
            score += 0.5
        
        # Tide contribution (0-1)
        if tide >= 1.5:
            score += 1.0
        elif tide >= 1.0:
            score += 0.7
        elif tide >= 0.5:
            score += 0.3
        
        # RF propensity contribution (0-1.5)
        if rf == 2:
            score += 1.5
        elif rf == 1:
            score += 0.8
        
        # Map to risk universe (0-6)
        return np.clip(score * 1.2, 0, 6)


# Global instance
_fuzzy_system = None


def get_fuzzy_system() -> FuzzyFloodRisk:
    """Get or create the global fuzzy system instance"""
    global _fuzzy_system
    if _fuzzy_system is None:
        _fuzzy_system = FuzzyFloodRisk()
    return _fuzzy_system


def compute_flood_risk(water_level_mm: float, rate_of_rise_mm_day: float,
                       forecast_rain_mm: float, tide_level_m: float,
                       rf_propensity: int) -> Dict:
    """
    Convenience function to compute flood risk
    
    Args:
        water_level_mm: Current water level in mm
        rate_of_rise_mm_day: Rate of rise in mm/day
        forecast_rain_mm: Forecasted precipitation in mm/day
        tide_level_m: Current tide level in meters
        rf_propensity: RF model output (0=Low, 1=Medium, 2=High)
    
    Returns:
        Dictionary with risk assessment
    """
    system = get_fuzzy_system()
    return system.compute_risk(water_level_mm, rate_of_rise_mm_day,
                               forecast_rain_mm, tide_level_m, rf_propensity)


if __name__ == "__main__":
    # Test the fuzzy system
    print("Testing Fuzzy Flood Risk System...")
    
    system = FuzzyFloodRisk()
    
    # Test cases
    test_cases = [
        # (WL_mm, RoR_mm_day, FRain_mm, Tide_m, RF)
        (300, -50, 2, 0.3, 0),      # Rule 1: Receding
        (500, 0, 3, 0.4, 0),        # Rule 2: Receding
        (800, 0, 10, 0.5, 0),       # Rule 3: Receding
        (800, 50, 10, 0.5, 0),      # Rule 4: Alert
        (1000, 50, 20, 0.8, 0),     # Rule 5: Alert
        (1000, 50, 25, 1.0, 1),     # Rule 6: Alarm
        (1500, 200, 30, 1.2, 1),    # Rule 7: Alarm
        (2000, 300, 50, 2.0, 2),    # Rule 8: Critical
        (2000, 0, 3, 0.8, 0),       # Rule 9: Alert
        (2000, 0, 20, 1.2, 1),      # Rule 10: Alarm
        (2500, 100, 50, 2.0, 2),    # Rule 11: Critical
        (500, -50, 20, 1.0, 2),     # Rule 12: Alert
        (1000, -50, 50, 1.5, 2),    # Rule 13: Alarm
        (1500, 50, 20, 1.5, 2),     # Rule 14: Alarm
        (2000, 50, 20, 1.5, 2),     # Rule 15: Critical
    ]
    
    print("\nRunning test cases:")
    for i, (wl, ror, frain, tide, rf) in enumerate(test_cases, 1):
        result = system.compute_risk(wl, ror, frain, tide, rf)
        print(f"\nTest {i}: WL={wl}mm, RoR={ror}mm/d, FRain={frain}mm, Tide={tide}m, RF={RF_PROPENSITY_MAP[rf]}")
        print(f"  Risk: {result['risk_level']} (crisp={result['risk_crisp']})")
        print(f"  Rule triggered: {result['rule_triggered']}")