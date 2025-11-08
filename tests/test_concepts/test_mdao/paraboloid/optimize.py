# -*- coding: utf-8 -*-

import openmdao.api as om


class Paraboloid(om.ExplicitComponent):
    """
    Evaluates the equation f(x,y) = (x-3)^2 + xy + (y+4)^2 - 3.
    """

    def setup(self):
        self.add_input('x', val=0.0)
        self.add_input('y', val=0.0)

        self.add_output('f_xy', val=0.0)

    def setup_partials(self):
        # Finite difference all partials.
        self.declare_partials('*', '*', method='fd')

    def compute(self, inputs, outputs):
        """
        f(x,y) = (x-3)^2 + xy + (y+4)^2 - 3

        Minimum at: x = 6.6667; y = -7.3333
        """
        x = inputs['x']
        y = inputs['y']

        outputs['f_xy'] = (x - 3.0)**2 + x * y + (y + 4.0)**2 - 3.0
     
        
if __name__ == "__main__":

    
    # build the model
    prob = om.Problem()
    prob.model.add_subsystem('parab', Paraboloid(), promotes_inputs=['x', 'y'])
    
    # define the component whose output will be constrained
    prob.model.add_subsystem('const', om.ExecComp('g = x + y'), promotes_inputs=['x', 'y'])
    
    # Design variables 'x' and 'y' span components, so we need to provide a common initial
    # value for them.
    prob.model.set_input_defaults('x', 3.0)
    prob.model.set_input_defaults('y', -4.0)
    
    # setup the optimization
    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options['optimizer'] = 'COBYLA'
    
    prob.model.add_design_var('x', lower=-50, upper=50)
    prob.model.add_design_var('y', lower=-50, upper=50)
    prob.model.add_objective('parab.f_xy')
    
    # to add the constraint to the model
    prob.model.add_constraint('const.g', lower=0, upper=10.)
    prob.driver.options['debug_print'] = ['desvars','ln_cons','nl_cons','objs']
    prob.setup()
    prob.run_driver();